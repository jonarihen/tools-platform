import ast
import logging
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

from flask import Flask, request


class PasswordLimitTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).with_name('app.py')
        tree = ast.parse(source.read_text())
        names = {'_validate_share_password', '_get_share_password_from_request'}
        nodes = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
        self.verify = Mock(return_value=False)
        self.namespace = {
            'request': request, 'time': time, 'logger': logging.getLogger(__name__),
            '_rate_limit_lock': threading.Lock(), '_rate_limit_stores': {},
            'SHARE_PASSWORD_FAIL_LIMIT': 10, 'SHARE_PASSWORD_FAIL_WINDOW': 900,
            'check_password_hash': self.verify,
        }
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), self.namespace)
        self.app = Flask(__name__)
        self.row = {'share_id': 'abc', 'password_hash': 'hash'}

    def attempt(self, ip='proxy-ip'):
        with self.app.test_request_context(json={'password': 'secret'}, headers={'X-Real-IP': ip}):
            return self.namespace['_validate_share_password'](self.row, 'slug')

    def test_blocked_attempts_never_hash_even_correct_password(self):
        for _ in range(10):
            self.assertEqual(self.attempt()[1], 401)
        self.verify.return_value = True
        self.assertEqual(self.attempt()[1], 429)
        self.assertEqual(self.verify.call_count, 10)
        self.assertIsNone(self.attempt('other-ip'))

    def test_success_does_not_consume_failure_budget(self):
        self.verify.return_value = True
        for _ in range(20):
            self.assertIsNone(self.attempt())
        self.verify.return_value = False
        self.assertEqual(self.attempt()[1], 401)

    def test_expired_failures_allow_retry(self):
        self.namespace['_rate_limit_stores']['share-password-fail:abc'] = {
            'proxy-ip': [time.time() - 901] * 10,
        }
        self.assertEqual(self.attempt()[1], 401)

    def test_concurrent_attempts_reserve_before_hashing(self):
        entered = threading.Event()
        release = threading.Event()
        lock = threading.Lock()
        count = 0

        def verify(*args):
            nonlocal count
            with lock:
                count += 1
                if count == 10:
                    entered.set()
            release.wait(5)
            return False

        self.verify.side_effect = verify
        with ThreadPoolExecutor(max_workers=10) as executor:
            pending = [executor.submit(self.attempt) for _ in range(10)]
            try:
                self.assertTrue(entered.wait(5))
                self.assertEqual(self.attempt()[1], 429)
                self.assertEqual(self.verify.call_count, 10)
            finally:
                release.set()
            self.assertTrue(all(future.result()[1] == 401 for future in pending))


if __name__ == '__main__':
    unittest.main()
