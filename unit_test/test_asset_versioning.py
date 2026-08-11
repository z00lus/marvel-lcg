from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urljoin

# Match the application's normal import order without starting the server.
from engine import Engine

from engine.device.web.server.server_files import GameServerFiles
from engine.network.web_server import AssetVersion, WebServer


class TestRewriteHtml(unittest.TestCase):

    def setUp(self):
        patcher = patch.object(AssetVersion, '_token', 'abcdef123456')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_local_code_is_prefixed_and_queries_survive(self):
        html = (
            '<link rel="stylesheet" href="/public/css/solo.css">\n'
            '<script type="module" src="/public/js/solo.js?ronin-session=1"></script>'
        )

        rewritten = AssetVersion.RewriteHtml(html)

        self.assertIn('href="/v/abcdef123456/public/css/solo.css"', rewritten)
        self.assertIn(
            'src="/v/abcdef123456/public/js/solo.js?ronin-session=1"',
            rewritten,
        )

    def test_everything_else_is_left_alone(self):
        html = (
            '<link rel="icon" href="/favicon.ico?ronin=1">\n'
            '<script src="https://cdn.example.com/x.js"></script>\n'
            '<script src="//cdn.example.com/y.js"></script>\n'
            '<img src="/public/images/logo.png">\n'
            '<a href="/main">Main menu</a>\n'
            '''<button onclick="Open('/solo?ronin-session=1')">Solo</button>'''
        )

        self.assertEqual(AssetVersion.RewriteHtml(html), html)

    def test_rewriting_twice_does_not_stack_prefixes(self):
        html = '<script src="/public/js/solo.js"></script>'

        once = AssetVersion.RewriteHtml(html)
        twice = AssetVersion.RewriteHtml(once)

        self.assertEqual(once, twice)
        self.assertEqual(twice.count('/v/'), 1)

    def test_single_quotes_and_spaced_attributes_are_handled(self):
        html = "<script src = '/public/js/solo.js'></script>"

        rewritten = AssetVersion.RewriteHtml(html)

        self.assertIn("'/v/abcdef123456/public/js/solo.js'", rewritten)

    def test_a_dot_before_the_extension_does_not_truncate_the_url(self):
        html = '<script src="/public/js/lib/sortable.min.js"></script>'

        rewritten = AssetVersion.RewriteHtml(html)

        self.assertIn('"/v/abcdef123456/public/js/lib/sortable.min.js"', rewritten)


class TestModuleGraphIsVersioned(unittest.TestCase):
    """The property the whole design rests on.

    A query string is not inherited by a relative import, so query-string
    versioning busts the entry point and leaves its dependencies stale. A path
    prefix is inherited. This asserts the difference with the same resolution
    rule the browser uses, so the claim is checked rather than assumed.
    """

    def test_a_path_prefix_is_inherited_by_relative_imports(self):
        # Both real cases: a sibling import from solo.js, and the parent-relative
        # import marvel/marvel.js uses to reach the vendored libs.
        self.assertEqual(
            urljoin('/v/abcdef123456/public/js/solo.js', './marvelcdb_deck.js'),
            '/v/abcdef123456/public/js/marvelcdb_deck.js',
        )
        self.assertEqual(
            urljoin('/v/abcdef123456/public/js/marvel/marvel.js',
                    '../lib/sortable.js'),
            '/v/abcdef123456/public/js/lib/sortable.js',
        )

    def test_a_query_string_is_not_inherited(self):
        entry = '/public/js/solo.js?v=abcdef123456'

        # The dependency drops the token entirely -- this is the stale copy.
        self.assertEqual(
            urljoin(entry, './marvelcdb_deck.js'),
            '/public/js/marvelcdb_deck.js',
        )


class TestStripPrefix(unittest.TestCase):

    def test_a_versioned_path_is_reduced_to_the_real_one(self):
        self.assertEqual(
            AssetVersion.StripPrefix('/v/abcdef123456/public/js/solo.js'),
            ('/public/js/solo.js', True),
        )

    def test_unversioned_and_malformed_prefixes_pass_through(self):
        for path in [
            '/public/js/solo.js',
            './public/solo.html',
            '/v/short/public/js/solo.js',          # token too short
            '/v/ABCDEF123456/public/js/solo.js',   # not lowercase hex
            '/v/abcdef12345g/public/js/solo.js',   # not hex
            '/v/abcdef123456',                     # no trailing path
            '/version/public/js/solo.js',
        ]:
            with self.subTest(path=path):
                self.assertEqual(AssetVersion.StripPrefix(path), (path, False))

    def test_any_well_formed_token_resolves(self):
        """An old page must reach the file that exists now, not a 404."""
        stripped, versioned = AssetVersion.StripPrefix(
            '/v/000000000000/public/js/solo.js')
        self.assertEqual((stripped, versioned), ('/public/js/solo.js', True))

    def test_only_the_current_token_is_recognised_as_current(self):
        with patch.object(AssetVersion, '_token', 'abcdef123456'):
            self.assertTrue(AssetVersion.HasCurrentPrefix(
                '/v/abcdef123456/public/js/solo.js'))
            self.assertFalse(AssetVersion.HasCurrentPrefix(
                '/v/000000000000/public/js/solo.js'))
            self.assertFalse(AssetVersion.HasCurrentPrefix(
                '/public/js/solo.js'))


class TestComputeToken(unittest.TestCase):

    def _token_for(self, folder: str) -> str:
        with patch.object(AssetVersion, 'FOLDERS', (folder,)):
            return AssetVersion.Compute()

    def test_the_token_tracks_content(self):
        with tempfile.TemporaryDirectory() as folder:
            nested = os.path.join(folder, 'lib')
            os.makedirs(nested)
            asset = os.path.join(nested, 'a.js')
            with open(asset, 'w', encoding='utf-8') as file:
                file.write('one')

            first = self._token_for(folder)
            self.assertEqual(self._token_for(folder), first)   # stable
            self.assertRegex(first, r'^[0-9a-f]{12}$')

            with open(asset, 'w', encoding='utf-8') as file:
                file.write('two')
            changed = self._token_for(folder)
            self.assertNotEqual(changed, first)

            # A rename with identical bytes still changes the build.
            os.rename(asset, os.path.join(nested, 'b.js'))
            self.assertNotEqual(self._token_for(folder), changed)

    def test_a_missing_folder_is_not_fatal(self):
        with tempfile.TemporaryDirectory() as folder:
            token = self._token_for(os.path.join(folder, 'absent'))
            self.assertRegex(token, r'^[0-9a-f]{12}$')

    def test_the_token_is_memoised(self):
        AssetVersion.Reset()
        with patch.object(AssetVersion, 'Compute', return_value='0123456789ab') as compute:
            self.assertEqual(AssetVersion.Token(), '0123456789ab')
            self.assertEqual(AssetVersion.Token(), '0123456789ab')
        compute.assert_called_once()
        AssetVersion.Reset()


class TestResponseHeaders(unittest.TestCase):

    def setUp(self):
        self.server = WebServer()

    def test_a_versioned_url_is_served_immutable(self):
        with tempfile.TemporaryDirectory() as folder:
            os.makedirs(os.path.join(folder, 'public', 'js'))
            asset = os.path.join(folder, 'public', 'js', 'probe.js')
            with open(asset, 'w', encoding='utf-8') as file:
                file.write('export const probe = 1;\n')

            with patch.object(AssetVersion, '_token', 'abcdef123456'):
                response = self.server.ReadFile(
                    '/v/abcdef123456/public/js/probe.js', [folder])

            self.assertEqual(response.status, 200)
            self.assertIn('immutable', response.headers['Cache-Control'])
            self.assertEqual(bytes(response.body).decode(), 'export const probe = 1;\n')

    def test_an_old_versioned_url_is_served_but_not_cached(self):
        with tempfile.TemporaryDirectory() as folder:
            os.makedirs(os.path.join(folder, 'public', 'js'))
            asset = os.path.join(folder, 'public', 'js', 'probe.js')
            with open(asset, 'w', encoding='utf-8') as file:
                file.write('export const probe = 2;\n')

            with patch.object(AssetVersion, '_token', 'abcdef123456'):
                response = self.server.ReadFile(
                    '/v/000000000000/public/js/probe.js', [folder])

            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            self.assertNotIn('immutable', response.headers['Cache-Control'])
            self.assertEqual(bytes(response.body).decode(), 'export const probe = 2;\n')

    def test_a_missing_file_is_never_cached(self):
        response = self.server.ReadFile('/public/js/does-not-exist.js')

        self.assertEqual(response.status, 404)
        cache_control = response.headers['Cache-Control']
        self.assertEqual(cache_control, 'no-store')
        # The regression: a year-long max-age on a 404 meant a file added later
        # stayed missing until the browser cache was cleared by hand.
        self.assertNotIn('max-age', cache_control)

    def test_a_page_is_not_cached_and_carries_the_token(self):
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, 'probe.html'), 'w', encoding='utf-8') as file:
                file.write('<script src="/public/js/solo.js"></script>')

            with patch.object(AssetVersion, '_token', 'abcdef123456'):
                response = self.server.ReadHtmlFile('probe.html', [folder])

            self.assertEqual(response.status, 200)
            self.assertEqual(
                response.headers['Cache-Control'], 'no-cache, must-revalidate')
            self.assertIn(
                '/v/abcdef123456/public/js/solo.js',
                bytes(response.body).decode(),
            )

    def test_a_missing_page_is_not_cached_either(self):
        response = self.server.ReadHtmlFile('./public/does-not-exist.html')

        self.assertEqual(response.status, 404)
        # Asserted as no-store rather than merely "no max-age": ReadHtmlFile
        # used to stamp `no-cache` over every response including 404s, which
        # made a max-age assertion here pass no matter what ReadFile returned.
        self.assertEqual(response.headers['Cache-Control'], 'no-store')


class TestPrimaryPageHandlers(unittest.TestCase):

    def setUp(self):
        self.server = GameServerFiles()

    def test_table_handler_versions_the_real_game_page(self):
        with patch.object(AssetVersion, '_token', 'abcdef123456'):
            response = asyncio.run(self.server.handle_marvel(None))

        html = bytes(response.body).decode('utf-8')
        self.assertEqual(response.status, 200)
        self.assertEqual(
            response.headers['Cache-Control'], 'no-cache, must-revalidate')
        self.assertIn(
            '/v/abcdef123456/public/js/marvel/marvel.js', html)
        self.assertIn(
            '/v/abcdef123456/public/css/marvel/marvel.css', html)


if __name__ == '__main__':
    unittest.main()
