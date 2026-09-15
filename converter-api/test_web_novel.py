import ast
import html
import json
import re
import time
import unittest
from flask import Flask, request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


SOURCE = Path(__file__).with_name('app.py')
TREE = ast.parse(SOURCE.read_text())
NAMESPACE = {
    're': re, 'html': html, 'json': json, 'time': time,
    'urljoin': urljoin, 'urlparse': urlparse, 'BeautifulSoup': BeautifulSoup,
    'http_requests': requests, '_update_job': Mock(),
}
NODES = []
IN_SCRAPER = False
for node in TREE.body:
    if isinstance(node, ast.FunctionDef) and node.name == '_safe_pdf_name':
        IN_SCRAPER = True
    if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id.startswith(('WEB_NOVEL_', 'WEBNOVEL_', 'ROYALROAD_', 'SCRIBBLEHUB_'))
        for target in node.targets
    ):
        NODES.append(node)
    elif isinstance(node, ast.FunctionDef) and IN_SCRAPER:
        if node.name == 'get_progress':
            break
        node.decorator_list = []
        NODES.append(node)
exec(compile(ast.Module(body=NODES, type_ignores=[]), str(SOURCE), 'exec'), NAMESPACE)
api = SimpleNamespace(**NAMESPACE)


def response(text='', status=200, headers=None):
    result = requests.Response()
    result.status_code = status
    result.headers.update(headers or {})
    result._content = text.encode()
    result._content_consumed = True
    return result


class ScraperTests(unittest.TestCase):
    def soup(self, text):
        return BeautifulSoup(text, 'html.parser')

    def extract(self, function, pages, *args):
        with patch.dict(NAMESPACE, {
            '_fetch_allowed_response': Mock(side_effect=[(response(page), url) for page, url in pages]),
            'WEB_NOVEL_FETCH_DELAY': 0,
        }):
            return function(Mock(), *args)

    def test_normalisation(self):
        cases = {
            'royalroad.com/fiction/12/story/chapter/34/title': 'https://www.royalroad.com/fiction/12/story/',
            'https://scribblehub.com/read/12-story/chapter/34/': 'https://www.scribblehub.com/series/12/story/',
            'https://webnovel.com/book/story_12/chapter_34?token=secret': 'https://www.webnovel.com/book/story_12',
            'https://webnovel.com/book/story_12/catalog': 'https://www.webnovel.com/book/story_12',
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(api._normalise_web_novel_url(raw)[0], expected)

    def test_invalid_urls(self):
        for url in ('https://webnovel.com.evil/book/x_1', 'file:///etc/passwd',
                    'https://user:pass@webnovel.com/book/x_1', 'https://webnovel.com:444/book/x_1',
                    'https://webnovel.com/book/x', 'https://127.0.0.1/fiction/1'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                api._normalise_web_novel_url(url)

    def test_hidden_before_sanitising(self):
        soup = self.soup('''<style>.noise, .body .decoy {display:none!important}
            .ghost {visibility:hidden}</style><div class="body"><p>Keep <em>this</em></p>
            <p class="noise">bad1</p><p class="decoy">bad2</p><p hidden>bad3</p>
            <p aria-hidden="TRUE">bad4</p><p style="color:red; display: none">bad5</p>
            <p class="ghost">bad6</p><p style="opacity:0">bad7</p></div>''')
        api._remove_hidden_content(soup)
        cleaned = api._sanitise_fragment(soup.select_one('.body'))
        self.assertNotIn('bad', cleaned)
        self.assertIn('<em>this</em>', cleaned)

    def test_uncertain_css_preserves_prose(self):
        cases = [
            ('.text {display:none} .text {display:block}', ''),
            ('@media print {.text {display:none}}', ''),
            ('.text {display:none} @media screen {.text {display:block}}', ''),
            ('#prose {display:block} .text {display:none}', ''),
            ('.text {display:none!important} #prose {display:block!important}', ''),
            ('.text {display:none}', 'display:block'),
            ('.text {display:block!important}', 'display:none'),
            ('', 'display:none;display:block'),
            ('.text {display:none} .text:hover {display:block}', ''),
            ('.text {display:none} .text {all:initial}', ''),
        ]
        for css, inline in cases:
            with self.subTest(css=css, inline=inline):
                soup = self.soup(f'<style>{css}</style><div class="body"><p id="prose" class="text" style="{inline}">Visible prose</p></div>')
                api._remove_hidden_content(soup)
                cleaned = api._sanitise_fragment(soup.select_one('.body'))
                self.assertIn('Visible prose', cleaned)

    def test_media_stylesheet_and_visibility_override_preserve_prose(self):
        for markup in (
            '<style media="print">.text {display:none}</style><p class="text">Visible prose</p>',
            '<style>.parent {visibility:hidden} .text {visibility:visible}</style><div class="parent"><p class="text">Visible prose</p></div>',
            '<style>.hidden {display:none} .hidden {display:block}</style><p class="hidden">Visible prose</p>',
            '<link rel="stylesheet" href="/site.css"><p style="display:none">Visible prose</p>',
        ):
            with self.subTest(markup=markup):
                self.assertIn('Visible prose', api._sanitise_fragment(self.soup(markup)))

    def test_decorative_catalog_svg_is_not_locked(self):
        for svg in ('<svg/>', '<svg><use href="#i-star"/></svg>', '<svg><use xlink:href="#i-unlock"/></svg>'):
            with self.subTest(svg=svg):
                catalog = api._webnovel_catalog(self.soup(
                    '<li data-cid="1"><a href="/book/story_12/start_1">One</a>' + svg + '</li>'
                ), 'https://www.webnovel.com/book/story_12')
                self.assertFalse(catalog[0]['locked'])

    def test_sanitiser_blocks_active_resources(self):
        cleaned = api._sanitise_fragment(self.soup('''<div background="file:///etc/passwd">
            <object data="http://localhost"></object><img src="http://localhost">
            <a href="javascript:alert(1)" onmouseover="evil()">Read</a>
            <p style="background:url(http://localhost)">Text</p></div>'''))
        for value in ('localhost', 'javascript', 'onmouseover', 'file:', 'background'):
            self.assertNotIn(value, cleaned)
        self.assertIn('Text', cleaned)

    def test_redirect_security(self):
        for target in ('https://evil.test/x', 'http://127.0.0.1/',
                       'https://user:pass@www.royalroad.com/x', 'file:///etc/passwd'):
            session = Mock()
            session.get.return_value = response(status=302, headers={'Location': target})
            with self.subTest(target=target), self.assertRaises(RuntimeError):
                api._fetch_allowed_response(session, 'https://www.royalroad.com/fiction/1', api.ROYALROAD_HOSTS)
            self.assertEqual(session.get.call_count, 1)
            self.assertFalse(session.get.call_args.kwargs['allow_redirects'])

    def test_redirect_loop_and_relative_redirect(self):
        session = Mock()
        session.get.side_effect = [response(status=302, headers={'Location': '/fiction/2'}), response('OK')]
        result, final = api._fetch_allowed_response(session, 'https://www.royalroad.com/fiction/1', api.ROYALROAD_HOSTS)
        self.assertEqual(result.text, 'OK')
        self.assertEqual(final, 'https://www.royalroad.com/fiction/2')
        session.get.side_effect = None
        session.get.return_value = response(status=302, headers={'Location': '/loop'})
        with self.assertRaisesRegex(RuntimeError, 'Too many redirects'):
            api._fetch_allowed_response(session, final, api.ROYALROAD_HOSTS)

    def test_session_has_no_environment_credentials(self):
        with api._build_web_novel_session() as session:
            self.assertFalse(session.trust_env)
            self.assertIsNone(session.auth)

    def test_response_size_limit(self):
        result = Mock()
        result.iter_content.return_value = [b'x' * (10 * 1024 * 1024 + 1)]
        with self.assertRaisesRegex(RuntimeError, '10 MB'):
            api._read_source_response(result)
        result.close.assert_called_once()

    def test_retry_and_challenge(self):
        with patch.dict(NAMESPACE, {'WEB_NOVEL_RETRY_BACKOFF': 0}):
            fetch = Mock(side_effect=[response(status=429), response(status=502), response('ok')])
            self.assertEqual(api._retry_fetch(fetch).text, 'ok')
            self.assertEqual(fetch.call_count, 3)
            with self.assertRaisesRegex(RuntimeError, 'Cloudflare'):
                api._retry_fetch(lambda: response('Just a moment', 403))
            with self.assertRaisesRegex(RuntimeError, 'Connection'):
                api._retry_fetch(Mock(side_effect=requests.Timeout))

    def test_ranges(self):
        self.assertEqual(api._select_chapters(['a', 'b', 'c'], 2, 2), [(2, 'b')])
        for start, end in ((0, 1), (2, 1), (1, 4), (4, None)):
            with self.assertRaises(ValueError):
                api._select_chapters(['a', 'b', 'c'], start, end)
        with self.assertRaises(ValueError):
            api._select_chapters(list(range(1001)))

    def test_webnovel_catalog_locks_and_deduplication(self):
        catalog = api._webnovel_catalog(self.soup('''<li data-cid="1"><a href="/book/story_12/start_1">One</a></li>
            <li data-cid="1"><a href="/book/story_12/start_1">One</a></li>
            <li data-cid="2"><svg><use href="#i-lock"/></svg>Two</li>'''), 'https://www.webnovel.com/book/story_12')
        self.assertEqual(len(catalog), 2)
        self.assertFalse(catalog[0]['locked'])
        self.assertTrue(catalog[1]['locked'])
        with self.assertRaises(RuntimeError):
            api._webnovel_catalog(self.soup('<li data-cid="1"><a href="https://evil.test/start_1">Bad</a></li>'), 'https://www.webnovel.com/book/story_12')

    def test_webnovel_partial_export(self):
        url = 'https://www.webnovel.com/book/story_12'
        pages = [('<h1>Story</h1><meta name="author" content="Writer">', url),
                 ('''<li data-cid="1"><a href="/book/story_12/start_1">One</a></li>
                     <li data-cid="2"><svg><use href="#i-lock"/></svg>Two</li>
                     <li data-cid="3"><a href="/book/story_12/end_3">Three</a></li>''', url + '/catalog'),
                 ('<h1>One</h1><div class="cha-content"><p>Public text</p></div>', url + '/start_1'),
                 ('<div class="cha-content _lock">Preview must not export</div>', url + '/end_3')]
        metadata, chapters = self.extract(api._extract_webnovel_chapters, pages, url, False, 'job')
        self.assertEqual(metadata['skipped_chapters'], [2, 3])
        self.assertEqual(len(chapters), 1)
        self.assertEqual(metadata['author'], 'Writer')
        document = api._build_web_novel_html(metadata, chapters, url, None)
        self.assertIn('Skipped locked chapters: 2, 3', document)
        self.assertNotIn('Preview', document)

    def test_webnovel_all_locked_and_missing_catalog(self):
        url = 'https://www.webnovel.com/book/story_12'
        for catalog, message in (('<li data-cid="2"><svg><use xlink:href="#i-lock"/></svg></li>', 'No public readable'), ('<div/>', 'No server-rendered')):
            with self.assertRaisesRegex(RuntimeError, message):
                self.extract(api._extract_webnovel_chapters, [('<h1>Story</h1>', url), (catalog, url + '/catalog')], url, False, 'job')

    def test_royalroad_regression_range_notes_hidden(self):
        url = 'https://www.royalroad.com/fiction/12/story/'
        series = '''<h1>Story</h1><div class="mt-card-name">Writer</div><table id="chapters">
            <tr class="chapter-row"><td><a href="/fiction/12/story/chapter/1/one">One</a></td></tr>
            <tr class="chapter-row"><td><a href="/fiction/12/story/chapter/2/two">Two</a></td></tr></table>'''
        chapter = '''<style>.noise {display:none}</style><h1>Two</h1><div class="chapter-content">
            <p>Hello</p><p class="noise">Noise</p></div><div class="author-note-portlet"><div class="portlet-body">Note</div></div>'''
        metadata, chapters = self.extract(api._extract_royalroad_chapters, [(series, url), (chapter, url)], url, True, 'job', 2, 2)
        self.assertEqual(metadata['title'], 'Story')
        self.assertEqual(len(chapters), 1)
        self.assertNotIn('Noise', chapters[0]['html'])
        self.assertIn('Note', chapters[0]['notes'][0])
        self.assertIn('positions 2–2', metadata['export_summary'])

    def test_scribblehub_regression(self):
        url = 'https://www.scribblehub.com/series/12/story/'
        with patch.dict(NAMESPACE, {'_fetch_scribblehub_toc': Mock(return_value=[{'url': '/read/12-story/chapter/1/', 'title': 'One'}])}):
            metadata, chapters = self.extract(api._extract_scribblehub_chapters, [
                ('<div class="fic_title">Story</div><div class="auth_name_fic">Writer</div>', url),
                ('<div id="chp_raw"><p>Text</p><p hidden>Noise</p></div>', url),
            ], url, False, 'job')
        self.assertEqual(metadata['author'], 'Writer')
        self.assertIn('Text', chapters[0]['html'])
        self.assertNotIn('Noise', chapters[0]['html'])
        self.assertEqual(chapters[0]['notes'], [])

    def test_scribblehub_post_redirect_and_repeated_pages(self):
        session = Mock()
        session.post.return_value = response(status=302, headers={'Location': 'https://evil.test'})
        with self.assertRaisesRegex(RuntimeError, 'Unexpected redirect'):
            api._fetch_scribblehub_toc(session, '12')
        self.assertFalse(session.post.call_args.kwargs['allow_redirects'])
        session.post.return_value = response('<li class="toc_w"><a class="toc_a" href="/read/12-story/chapter/1/">One</a></li>')
        with patch.dict(NAMESPACE, {'WEB_NOVEL_FETCH_DELAY': 0}), self.assertRaisesRegex(RuntimeError, 'pagination repeated'):
            api._fetch_scribblehub_toc(session, '12')

    def test_api_rejects_invalid_ranges_before_starting_job(self):
        flask_app = Flask(__name__)
        with patch.dict(NAMESPACE, {'request': request, '_check_rate_limit': Mock(return_value=True)}):
            for start, end in (('0', ''), ('3', '2'), ('1.5', '3'), ('1', '1001')):
                with flask_app.test_request_context('/', method='POST', data={
                    'url': 'https://www.webnovel.com/book/story_12',
                    'start_chapter': start, 'end_chapter': end,
                }):
                    result, status = api.start_web_novel_to_pdf()
                    self.assertEqual(status, 400)
                    self.assertIn('error', result)

    def test_conversion_preserves_partial_summary(self):
        metadata = {'title': 'Story', 'export_summary': 'Exported 1 of 2. Skipped locked chapters: 2.'}
        update = Mock()
        session = Mock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=False)
        renderer = Mock()
        with patch.dict(NAMESPACE, {
            '_build_web_novel_session': Mock(return_value=session),
            '_source_adapter': Mock(return_value=Mock(return_value=(metadata, [{'title': 'One'}]))),
            '_update_job': update, '_render_web_novel_pdf': renderer,
            '_track_event_internal': Mock(), 'shutil': Mock(), 'os': __import__('os'),
            'UPLOAD_DIR': '/tmp/opencode',
        }):
            api._run_web_novel_conversion('job', 'https://www.webnovel.com/book/story_12', '/tmp/opencode/result.pdf', False, 'a4', 15, 12)
        self.assertEqual(update.call_args.kwargs['message'], metadata['export_summary'])
        self.assertEqual(update.call_args.kwargs['status'], 'done')
        renderer.assert_called_once()

    def test_webnovel_range_does_not_fetch_unselected_chapters(self):
        url = 'https://www.webnovel.com/book/story_12'
        pages = [('<h1>Story</h1>', url),
                 ('<li data-cid="1"><svg><use xlink:href="#i-lock"/></svg></li><li data-cid="2"><a href="/book/story_12/two_2">Two</a></li>', url + '/catalog'),
                 ('<div class="cha-content">Second chapter</div>', url + '/two_2')]
        metadata, chapters = self.extract(api._extract_webnovel_chapters, pages, url, False, 'job', 2, 2)
        self.assertEqual(metadata['skipped_chapters'], [])
        self.assertEqual(metadata['selected_count'], 1)
        self.assertIn('Second chapter', chapters[0]['html'])

    def test_cover_rejects_svg_disguised_as_image(self):
        with patch.dict(NAMESPACE, {'_fetch_allowed_response': Mock(return_value=(response('<svg><use xlink:href="#i-lock"/></svg>', headers={'Content-Type': 'image/png'}), 'url'))}):
            self.assertIsNone(api._download_cover_asset(Mock(), 'https://www.scribblehub.com/cover.png', '/tmp/opencode'))

    def test_source_adapters(self):
        self.assertIs(api._source_adapter('www.royalroad.com'), api._extract_royalroad_chapters)
        self.assertIs(api._source_adapter('www.scribblehub.com'), api._extract_scribblehub_chapters)
        self.assertIs(api._source_adapter('www.webnovel.com'), api._extract_webnovel_chapters)
        with self.assertRaises(ValueError):
            api._source_adapter('evil.test')


if __name__ == '__main__':
    unittest.main()
