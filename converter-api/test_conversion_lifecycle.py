import ast
import logging
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock


def load_functions(names, namespace):
    source = Path(__file__).with_name('app.py')
    nodes = [node for node in ast.parse(source.read_text()).body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    for node in nodes:
        node.decorator_list = []
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
    return namespace


class ConversionDeadlineTests(unittest.TestCase):
    def test_stalled_pipe_times_out_and_reaps(self):
        for script in ('import time; time.sleep(30)',
                       'import sys,time; sys.stdout.write("partial"); sys.stdout.flush(); time.sleep(30)',
                       'import os,time; os.close(1); os.close(2); time.sleep(30)'):
            with self.subTest(script=script), tempfile.TemporaryDirectory() as directory:
                children = []

                def spawn(*args, **kwargs):
                    child = subprocess.Popen(*args, **kwargs)
                    children.append(child)
                    return child

                proxy = Mock(Popen=spawn, TimeoutExpired=subprocess.TimeoutExpired,
                             PIPE=subprocess.PIPE, STDOUT=subprocess.STDOUT)
                update = Mock()
                namespace = load_functions({'_run_conversion'}, {
                    'subprocess': proxy, 'selectors': selectors, 'signal': signal,
                    'os': os, 'time': time, 'shutil': shutil, 'CALIBRE_TIMEOUT': 0.15,
                    'UPLOAD_DIR': directory, '_update_job': update,
                    'logger': logging.getLogger(__name__), '_parse_line': lambda line: (None, line),
                })
                paths = [str(Path(directory) / name) for name in ('input.epub', 'book.htmlz', 'book.pdf')]
                Path(paths[0]).touch()
                started = time.monotonic()
                namespace['_run_conversion']('job', *paths, [sys.executable, '-c', script], 'a4', '15', '13')
                self.assertLess(time.monotonic() - started, 2)
                self.assertIsNotNone(children[0].returncode)
                self.assertTrue(children[0].stdout.closed)
                self.assertFalse(Path(paths[0]).exists())
                update.assert_called_with('job', status='error', message='Conversion timed out after 15 minutes')


if __name__ == '__main__':
    unittest.main()
