"""Route-level checks for the MarvelCDB deck endpoints.

The service tests cover the rules; these cover the HTTP edges -- a malformed
body and a hostile `hero_id` must come back as a 400, not as a 500 and not as a
file operation outside the campaign folder.

The handlers are exercised directly on an instance built with `object.__new__`,
which skips `GameServerBase.__init__` and its route registration. That keeps the
test to the request/response contract without standing up a server.
"""

import asyncio
import json
import os
import tempfile
import unittest

from engine.device.web.server.server_marvelcdb import GameServerMarvelCdb
from engine.lib import Json
from engine.marvelcdb.deck_sync import MarvelCdbDeckSync

from unit_test.test_marvelcdb_sync import SPIDER_MAN_TEMPLATE


class FakeRequest:
    """Only the part of web.Request the handlers touch."""

    def __init__(self, body, *, raise_on_json: bool = False) -> None:
        self._body = body
        self._raise_on_json = raise_on_json

    async def json(self):
        if self._raise_on_json:
            raise ValueError('not json')
        return self._body


class DeviceManager:

    def __init__(self, deck_sync: MarvelCdbDeckSync) -> None:
        self.marvelcdb_deck_sync = deck_sync


def build_server(folder: str) -> GameServerMarvelCdb:
    campaign = os.path.join(folder, 'campaign')
    os.makedirs(campaign, exist_ok=True)
    deck_sync = MarvelCdbDeckSync(
        user_deck_folder=os.path.join(folder, 'user'),
        campaign_deck_folder=campaign,
        state_file=os.path.join(folder, '.state.json'),
        starter_deck_folder=os.path.join(folder, 'starter'),
    )
    server = object.__new__(GameServerMarvelCdb)
    server.device_manager = DeviceManager(deck_sync)
    return server


def call(handler, request) -> tuple:
    response = asyncio.run(handler(request))
    return response.status, json.loads(response.text)


class TestMalformedBodies(unittest.TestCase):

    def _handlers(self, server):
        return [
            server.resolve_marvelcdb_deck,
            server.save_campaign_deck,
            server.refresh_campaign_deck,
        ]

    def test_a_body_that_is_not_json_is_a_400(self):
        with tempfile.TemporaryDirectory() as folder:
            server = build_server(folder)
            for handler in self._handlers(server):
                with self.subTest(handler=handler.__name__):
                    status, payload = call(
                        handler, FakeRequest(None, raise_on_json=True))
                    self.assertEqual(status, 400)
                    self.assertIn('error', payload)

    def test_json_that_is_not_an_object_is_a_400(self):
        with tempfile.TemporaryDirectory() as folder:
            server = build_server(folder)
            for handler in self._handlers(server):
                for body in [[], 'string', 7, None]:
                    with self.subTest(handler=handler.__name__, body=body):
                        status, payload = call(handler, FakeRequest(body))
                        self.assertEqual(status, 400)
                        self.assertIn('error', payload)

    def test_missing_fields_are_a_400(self):
        with tempfile.TemporaryDirectory() as folder:
            server = build_server(folder)
            cases = [
                (server.resolve_marvelcdb_deck, {}),
                (server.save_campaign_deck, {}),
                (server.save_campaign_deck, {'campaign_id': 'mutant_genesis'}),
                (server.save_campaign_deck,
                 {'campaign_id': 'mutant_genesis', 'deck': 'not-a-deck'}),
                (server.refresh_campaign_deck, {}),
                (server.refresh_campaign_deck, {'hero_id': '   '}),
            ]
            for handler, body in cases:
                with self.subTest(handler=handler.__name__, body=body):
                    status, payload = call(handler, FakeRequest(body))
                    self.assertEqual(status, 400)
                    self.assertIn('error', payload)


class TestHostileHeroId(unittest.TestCase):

    def test_traversal_is_a_400_and_leaves_the_target_alone(self):
        with tempfile.TemporaryDirectory() as folder:
            server = build_server(folder)

            outside_path = os.path.join(folder, 'outside.json')
            original = Json.Dumps(dict(SPIDER_MAN_TEMPLATE), indent=4)
            with open(outside_path, 'w', encoding='utf-8') as file:
                file.write(original)

            for hero_id in ['../outside', '../../outside', '/etc/passwd',
                            'sub/outside', 'name.with.dots']:
                with self.subTest(hero_id=hero_id):
                    status, payload = call(
                        server.refresh_campaign_deck,
                        FakeRequest({'hero_id': hero_id}),
                    )
                    # 400, not 500: a rejected name is a bad request, and a 500
                    # here would mean the guard raised something unhandled.
                    self.assertEqual(status, 400)
                    self.assertIn('Invalid campaign deck name', payload['error'])

            with open(outside_path, encoding='utf-8') as file:
                self.assertEqual(file.read(), original)

    def test_a_well_formed_but_unknown_id_is_still_a_400(self):
        """The guard must not swallow the ordinary not-found case."""
        with tempfile.TemporaryDirectory() as folder:
            server = build_server(folder)
            status, payload = call(
                server.refresh_campaign_deck,
                FakeRequest({'hero_id': 'mutant_genesis-01001a'}),
            )
            self.assertEqual(status, 400)
            self.assertIn('No campaign deck was saved', payload['error'])


if __name__ == '__main__':
    unittest.main()
