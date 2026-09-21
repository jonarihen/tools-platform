import ast
import io
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import threading
import time
import unittest
import uuid
from unittest.mock import Mock

from flask import Flask, request


class ShareNamespaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        database = str(Path(self.directory.name) / 'shares.db')

        def connect():
            conn = sqlite3.connect(database)
            conn.row_factory = sqlite3.Row
            return conn

        self.connect = connect
        with connect() as conn:
            conn.execute('CREATE TABLE shares (share_id TEXT PRIMARY KEY, filename TEXT, path TEXT, '
                         'expires_at REAL, size INTEGER, slug TEXT UNIQUE, password_hash TEXT)')
        source = Path(__file__).with_name('app.py')
        names = {'_db_get_share', 'slug_check', 'share_upload'}
        nodes = [node for node in ast.parse(source.read_text()).body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
        for node in nodes:
            node.decorator_list = []
        self.namespace = {
            '_db_connect': connect, '_db_lock': threading.Lock(), 'request': request,
            '_ID_RE': re.compile(r'^[a-f0-9]{16}$'),
            '_SLUG_RE': re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-]{1,48}[a-zA-Z0-9]$'),
            '_check_rate_limit': Mock(return_value=True), 'uuid': uuid, 're': re,
            'os': os, 'time': time, 'SHARE_DIR': self.directory.name,
            'MAX_TTL': 604800, 'MAX_SHARE_SIZE': 1000, 'MAX_TOTAL_SIZE': 10000,
            '_track_event_internal': Mock(),
        }
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), self.namespace)
        self.app = Flask(__name__)

    def insert(self, share_id, slug):
        with self.connect() as conn:
            conn.execute('INSERT INTO shares (share_id, slug, size) VALUES (?, ?, 0)', (share_id, slug))

    def test_id_precedence_and_legacy_slug_fallback(self):
        key = 'deadbeefdeadbeef'
        self.insert('1111111111111111', key)
        lookup = self.namespace['_db_get_share']
        self.assertEqual(lookup(key)['share_id'], '1111111111111111')
        self.insert(key, 'normal-slug')
        self.assertEqual(lookup(key)['share_id'], key)
        self.assertEqual(lookup('normal-slug')['share_id'], key)
        self.assertEqual(lookup('1111111111111111')['slug'], key)
        self.assertIsNone(lookup('missing-slug'))
        self.assertIsNone(lookup('../invalid'))

    def test_hex_slugs_rejected_in_both_endpoints(self):
        for slug in ('deadbeefdeadbeef', 'DEADBEEFDEADBEEF', '1234567890123456'):
            with self.subTest(slug=slug):
                with self.app.test_request_context(query_string={'slug': slug}):
                    self.assertEqual(self.namespace['slug_check']()[1], 400)
                with self.app.test_request_context(method='POST', data={
                    'slug': slug, 'file': (io.BytesIO(b'data'), 'file.txt'),
                }):
                    self.assertEqual(self.namespace['share_upload']()[1], 400)

    def test_normal_upload_avoids_existing_legacy_slug(self):
        self.insert('1111111111111111', 'deadbeefdeadbeef')
        self.namespace['uuid'] = Mock(uuid4=Mock(side_effect=[
            uuid.UUID('deadbeefdeadbeef' + '0' * 16),
            uuid.UUID('abcdefabcdefabcd0000000000000000'),
        ]))
        with self.app.test_request_context(query_string={'slug': 'my-book'}):
            self.assertTrue(self.namespace['slug_check']()['available'])
        with self.app.test_request_context(method='POST', data={
            'slug': 'my-book', 'file': (io.BytesIO(b'data'), 'file.txt'),
        }):
            result = self.namespace['share_upload']()
        self.assertEqual(result['share_id'], 'abcdefabcdefabcd')
        self.assertEqual(result['link_key'], 'my-book')
        self.assertEqual(self.namespace['_db_get_share']('my-book')['share_id'], result['share_id'])
        with self.app.test_request_context(query_string={'slug': 'my-book'}):
            self.assertFalse(self.namespace['slug_check']()['available'])


if __name__ == '__main__':
    unittest.main()
