import ast
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from flask import Flask, send_file


class JobExpiryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        source = Path(__file__).with_name('app.py')
        names = {'_update_job', '_expire_terminal_jobs', 'download_pdf'}
        nodes = [node for node in ast.parse(source.read_text()).body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
        for node in nodes:
            node.decorator_list = []
        self.jobs = {}
        self.namespace = {'_jobs': self.jobs, '_jobs_lock': threading.Lock(),
                          'time': time, 'os': os, 'JOB_TTL': 3600,
                          'send_file': send_file, 'threading': Mock()}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), self.namespace)

    def job(self, name, status, **fields):
        path = Path(self.directory.name) / (name + '.pdf')
        path.write_bytes(b'%PDF-test')
        self.jobs[name] = {'status': status, 'created': 1, 'pdf_path': str(path),
                           'out_name': name + '.pdf', **fields}
        return path

    def test_only_expired_terminal_jobs_removed(self):
        active = self.job('active', 'converting')
        recent = self.job('recent', 'done', completed_at=time.time())
        expired = self.job('expired', 'done', completed_at=1)
        failed = self.job('failed', 'error', completed_at=1)
        legacy = self.job('legacy', 'done')
        self.namespace['_expire_terminal_jobs']()
        self.assertEqual(set(self.jobs), {'active', 'recent', 'legacy'})
        self.assertTrue(all(path.exists() for path in (active, recent, legacy)))
        self.assertFalse(expired.exists())
        self.assertFalse(failed.exists())
        self.assertGreater(self.jobs['legacy']['completed_at'], 1)

    def test_all_terminal_updates_record_completion_once(self):
        for status in ('done', 'error'):
            self.job(status, 'converting')
            self.namespace['_update_job'](status, status=status)
            completed = self.jobs[status]['completed_at']
            self.assertGreater(completed, 1)
            self.namespace['_update_job'](status, status=status, message='updated')
            self.assertEqual(self.jobs[status]['completed_at'], completed)

    def test_failed_unlink_retains_job_for_retry(self):
        self.job('error', 'error', completed_at=1)
        with patch.object(os, 'remove', side_effect=PermissionError):
            self.namespace['_expire_terminal_jobs']()
        self.assertIn('error', self.jobs)

    def test_long_running_job_can_complete_and_download(self):
        self.job('book', 'converting')
        self.namespace['_expire_terminal_jobs']()
        with Flask(__name__).test_request_context():
            self.assertEqual(self.namespace['download_pdf']('book')[1], 400)
            self.namespace['_update_job']('book', status='done')
            self.namespace['_expire_terminal_jobs']()
            response = self.namespace['download_pdf']('book')
            response.direct_passthrough = False
            self.assertEqual(response.get_data(), b'%PDF-test')
            response.close()
            cleanup = self.namespace['threading'].Thread.call_args.kwargs['target']
            cleanup()
            self.assertEqual(self.namespace['download_pdf']('book')[1], 404)


if __name__ == '__main__':
    unittest.main()
