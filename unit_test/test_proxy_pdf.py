import asyncio
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from engine.lib import Ver
from engine.device.web.server.server_proxy import GameServerProxy
from engine.proxy import ProxyPdfResult
from engine.proxy.pdf_generator import ProxyPdfGenerator


def test_card_image() -> bytes:
    image = Image.new('RGB', (127, 178), (36, 68, 92))
    output = io.BytesIO()
    image.save(output, format='PNG')
    image.close()
    return output.getvalue()


class TestProxyCardComposition(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        Ver.Initialize()

    def test_hero_contains_every_gameplay_group_and_both_identity_faces(self):
        hero = {
            'name': 'Test Hero',
            'hero': ['10001a,10001b'],
            'hero_deck': ['10002', '10002'],
            'player_deck': ['10003'],
            'set_aside': ['10004a,10004b'],
            'obligations': ['10005'],
            'nemesis_set': ['10006'],
        }
        with patch.object(ProxyPdfGenerator, '_load_json', return_value=hero):
            name, cards = ProxyPdfGenerator.CollectHeroCards('test_hero')

        self.assertEqual(name, 'Test Hero')
        self.assertEqual(cards, [
            '10001a', '10001b',
            '10002', '10002',
            '10003',
            '10004a', '10004b',
            '10005',
            '10006',
        ])

    def test_scenario_merges_standard_and_expert_by_maximum_copy_count(self):
        standard = {
            'name': 'Test Villain',
            'villain': ['20001', '20002'],
            'schemes': ['20004a,20004b'],
            'encounters': ['20005', '20005'],
            'encounter_sets': ['standard'],
            'modular_sets': ['recommended'],
        }
        expert = {
            **standard,
            'villain': ['20002', '20003'],
            'encounter_sets': ['standard', 'expert'],
        }
        encounter_sets = {
            'standard': {'encounters': ['21001', '21001']},
            'expert': {'encounters': ['21002']},
            'recommended': {'encounters': ['22001']},
        }

        def load_json(load_type, content_id):
            if load_type == 'Campaign':
                return standard
            return encounter_sets[content_id]

        with patch.object(ProxyPdfGenerator, '_load_json', side_effect=load_json), \
                patch.object(ProxyPdfGenerator, '_find_optional_scenario', return_value=expert):
            name, cards = ProxyPdfGenerator.CollectScenarioCards('test_villain')

        self.assertEqual(name, 'Test Villain')
        self.assertEqual(cards.count('20001'), 1)
        self.assertEqual(cards.count('20002'), 1)
        self.assertEqual(cards.count('20003'), 1)
        self.assertEqual(cards.count('20005'), 2)
        self.assertEqual(cards.count('21001'), 2)
        self.assertEqual(cards.count('21002'), 1)
        self.assertEqual(cards.count('22001'), 1)
        self.assertIn('20004a', cards)
        self.assertIn('20004b', cards)

    def test_underling_replaces_placeholder_villain_and_keeps_one_of_each_stage(self):
        scenario = {
            'name': 'Choose One',
            'villain': ['30001', '30002'],
            'schemes': ['30004a,30004b'],
            'underling_sets': ['actual_underling'],
            'encounter_sets': [],
            'modular_sets': [],
        }
        underling = {
            'name': 'Actual Underling',
            'villain': ['31001', '31002'],
            'expert_villain': ['31002', '31003'],
            'encounters': ['31004'],
            'set_aside': ['31005a,31005b'],
        }

        def load_json(load_type, content_id):
            return scenario if load_type == 'Campaign' else underling

        with patch.object(ProxyPdfGenerator, '_load_json', side_effect=load_json), \
                patch.object(ProxyPdfGenerator, '_find_optional_scenario', return_value=None):
            _, cards = ProxyPdfGenerator.CollectScenarioCards(
                'choose_one',
                'actual_underling',
            )

        self.assertNotIn('30001', cards)
        self.assertNotIn('30002', cards)
        self.assertEqual(cards.count('31001'), 1)
        self.assertEqual(cards.count('31002'), 1)
        self.assertEqual(cards.count('31003'), 1)
        self.assertIn('31005a', cards)
        self.assertIn('31005b', cards)

    def test_traversal_like_content_ids_are_rejected(self):
        for value in ['../hero', 'folder/hero', '/etc/passwd', '', 'hero name']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    ProxyPdfGenerator.ValidateId(value, 'hero deck')

    def test_only_catalogued_out_of_print_scenarios_are_allowed(self):
        with patch.object(
                ProxyPdfGenerator,
                '_out_of_print_content_ids',
                return_value=({'captain_america'}, {'mutagen_formula'}),
                ):
            ProxyPdfGenerator._require_out_of_print('scenario', 'mutagen_formula')
            with self.assertRaisesRegex(ValueError, 'officially out-of-print'):
                ProxyPdfGenerator._require_out_of_print('scenario', 'rhino')

    def test_synced_deck_inherits_out_of_print_status_from_its_identity(self):
        heroes = {
            '1130039': {'hero': ['03001a,03001b']},
            'captain_america': {'hero': ['03001a,03001b']},
        }
        with patch.object(
                ProxyPdfGenerator,
                '_out_of_print_content_ids',
                return_value=({'captain_america'}, set()),
                ), patch.object(
                    ProxyPdfGenerator,
                    '_load_json',
                    side_effect=lambda load_type, content_id: heroes[content_id],
                    ):
            self.assertTrue(
                ProxyPdfGenerator._is_out_of_print_hero_deck('1130039')
            )

    def test_synced_deck_for_in_print_identity_is_rejected(self):
        heroes = {
            '1143133': {'hero': ['01001a,01001b']},
            'captain_america': {'hero': ['03001a,03001b']},
        }
        with patch.object(
                ProxyPdfGenerator,
                '_out_of_print_content_ids',
                return_value=({'captain_america'}, set()),
                ), patch.object(
                    ProxyPdfGenerator,
                    '_load_json',
                    side_effect=lambda load_type, content_id: heroes[content_id],
                    ):
            self.assertFalse(
                ProxyPdfGenerator._is_out_of_print_hero_deck('1143133')
            )

    def test_catalog_records_the_confirmed_ffg_out_of_print_products(self):
        catalog = ProxyPdfGenerator._load_json('SetInfo', 'sets_info.json')
        out_of_print_products = {
            name for name, product in catalog.items()
            if isinstance(product, dict) and product.get('out_of_print') is True
        }

        self.assertEqual(len(out_of_print_products), 38)
        self.assertIn('27. Sinister Motives', out_of_print_products)
        self.assertIn('40. NeXt Evolution', out_of_print_products)
        self.assertNotIn('1. Core Set', out_of_print_products)
        self.assertNotIn('42. Angel', out_of_print_products)


class TestProxyPdfOutput(unittest.TestCase):

    def test_ten_faces_create_two_valid_a4_pdf_pages(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch('engine.proxy.pdf_generator.Cache.LoadImage', return_value=test_card_image()):
            file_path = os.path.join(folder, 'test.pdf')
            pages = ProxyPdfGenerator._write_pdf(
                [f'{index:05d}' for index in range(10)],
                file_path,
            )

            self.assertEqual(pages, 2)
            with open(file_path, 'rb') as file:
                pdf = file.read()

        self.assertTrue(pdf.startswith(b'%PDF-1.4'))
        self.assertIn(b'/MediaBox [0 0 595.276 841.890]', pdf)
        self.assertIn(b'/Count 2', pdf)
        self.assertTrue(pdf.rstrip().endswith(b'%%EOF'))


class FakeRequest:

    def __init__(self, body, *, invalid_json: bool=False) -> None:
        self.body = body
        self.invalid_json = invalid_json

    async def json(self):
        if self.invalid_json:
            raise ValueError('not json')
        return self.body


class FakeGenerator:

    def __init__(self, result: ProxyPdfResult) -> None:
        self.result = result
        self.calls = []

    def Generate(self, *args):
        self.calls.append(args)
        return self.result


class TestProxyPdfRoute(unittest.TestCase):

    def test_malformed_request_is_a_400(self):
        server = object.__new__(GameServerProxy)
        response = asyncio.run(server.generate_proxy_pdf(
            FakeRequest(None, invalid_json=True),
        ))
        self.assertEqual(response.status, 400)
        self.assertIn('error', json.loads(response.text))

    def test_success_returns_attachment_and_server_location(self):
        async def run_inline(process, *args):
            # The project TaskManager intentionally owns worker lifecycle. A
            # direct handler test has no Engine.Shutdown(), so keep this unit
            # test synchronous instead of leaving its executor alive.
            return process(*args)

        with tempfile.TemporaryDirectory() as folder:
            file_path = os.path.join(folder, 'hero-proxy.pdf')
            with open(file_path, 'wb') as file:
                file.write(b'%PDF-1.4\n%%EOF\n')
            result = ProxyPdfResult(
                file_path=file_path,
                display_path='./proxy-output/hero-proxy.pdf',
                file_name='hero-proxy.pdf',
                card_faces=45,
                pages=5,
            )
            generator = FakeGenerator(result)
            server = object.__new__(GameServerProxy)
            server.proxy_pdf_generator = generator

            with patch(
                    'engine.device.web.server.server_proxy.TaskManager.ToThread',
                    new=run_inline,
                    ):
                response = asyncio.run(server.generate_proxy_pdf(FakeRequest({
                    'kind': 'hero',
                    'id': 'spider_man',
                })))

        self.assertEqual(response.status, 200)
        self.assertEqual(generator.calls, [('hero', 'spider_man', None)])
        self.assertIn('hero-proxy.pdf', response.headers['Content-Disposition'])
        self.assertEqual(response.headers['X-Proxy-Path'], './proxy-output/hero-proxy.pdf')
        self.assertEqual(response.headers['X-Proxy-Cards'], '45')
        self.assertEqual(response.headers['X-Proxy-Pages'], '5')


if __name__ == '__main__':
    unittest.main()
