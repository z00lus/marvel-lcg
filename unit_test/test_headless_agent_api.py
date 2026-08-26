import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from engine.lib import Json, Ver
from engine.device.web.server.server_agent import GameServerAgent
from tools import marvel_lcg_mcp
from tools.marvel_lcg_mcp import _compact_snapshot


class HeadlessAgentGameBuilderTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()

    def test_builds_the_same_rules_18_solo_descriptor_as_quick_game(self):
        descriptor = GameServerAgent.BuildSoloGame(
            'groot', 'klaw', expert=True, seed=12345,
        )

        self.assertEqual(descriptor.seed, 12345)
        self.assertEqual(descriptor.rules, ['v18_all'])
        self.assertFalse(descriptor.record_statistics)
        self.assertEqual(len(descriptor.hero_json), 1)
        self.assertEqual(Json.Loads(descriptor.hero_json[0])['name'], 'Groot')
        scenario = Json.Loads(descriptor.campaign_json)
        self.assertEqual(scenario['name'], 'Klaw')
        self.assertTrue(scenario['expert'])
        self.assertEqual(
            descriptor.encounter_set_names,
            list(dict.fromkeys(
                scenario['encounter_sets'] + scenario['modular_sets']
            )),
        )

    def test_underling_scenario_requires_and_merges_a_valid_underling(self):
        with self.assertRaisesRegex(ValueError, 'requires an underling'):
            GameServerAgent.BuildSoloGame('echo', 'art_museum_heist')

        descriptor = GameServerAgent.BuildSoloGame(
            'echo', 'art_museum_heist', underling_id='bullseye',
        )
        scenario = Json.Loads(descriptor.campaign_json)
        self.assertTrue(scenario['villain'])
        self.assertGreater(len(scenario['encounters']), 7)

    def test_content_ids_cannot_escape_configured_catalog_folders(self):
        for hostile in ('../groot', 'sub/groot', '/etc/passwd', '', 'has space'):
            with self.subTest(hostile=hostile):
                with self.assertRaisesRegex(ValueError, 'Invalid hero id'):
                    GameServerAgent.BuildSoloGame(hostile, 'klaw')

    def test_catalog_only_exposes_quick_game_scenarios(self):
        server = object.__new__(GameServerAgent)
        catalog = server._catalog()
        scenario_ids = {scenario['id'] for scenario in catalog['scenarios']}

        self.assertIn('rhino', scenario_ids)
        self.assertIn('klaw', scenario_ids)
        self.assertNotIn('sets_info', scenario_ids)
        self.assertNotIn('standard', scenario_ids)


class McpSnapshotTests(unittest.TestCase):

    def test_compact_prompt_resolves_target_and_resource_names(self):
        snapshot = {
            'status': 'awaiting_input',
            'game_id': 7,
            'step': 3,
            'outcome': None,
            'recent_log': ['> Player turn'],
            'world': {
                'round_id': 1,
                'phase': 'Player 1 Turn',
                'event_name': 'WhenPlayerInTurn',
                'prompt_last_text': 'Choose an action',
                'players': [{
                    'area_hero': [{
                        'id': 1, 'name': 'Groot', 'card_id': '16001a',
                        'card_type': 'hero', 'is_ready': True,
                        'is_face_up': True, 'bind_object_id': 0,
                        'cost': 0, 'info': {'health': 10}, 'traits': {},
                        'effects': [], 'resources': [],
                    }],
                    'hand_cards': [{
                        'id': 2, 'name': 'Energy', 'card_id': '01089',
                        'card_type': 'resource', 'is_ready': True,
                        'is_face_up': True, 'bind_object_id': 0,
                        'cost': 0, 'info': {}, 'traits': {},
                        'effects': [], 'resources': [22],
                    }],
                    'allies': [], 'supports': [], 'engaged_enemies': [],
                    'player_discard_pile': [], 'player_deck': [{}],
                    'obligations_area': [], 'environment_area': [],
                    'additional_deck': [], 'additional_discard_pile': [],
                    'special_decks': {}, 'resources': '',
                }],
                'area_villain': [{
                    'id': 9, 'name': 'Klaw', 'card_id': '01113',
                    'card_type': 'encounter-villain', 'is_ready': True,
                    'is_face_up': True, 'bind_object_id': 0,
                    'cost': 0, 'info': {'health': 12}, 'traits': {},
                    'effects': [], 'resources': [],
                }],
                'area_schemes_main': [], 'area_schemes_side': [],
                'area_environment': [], 'encounter_discard_pile': [],
                'area_evidence': [], 'area_mission': [], 'area_rule': [],
                'area_boost': [], 'additional_decks': [],
                'additional_discard_piles': [],
                'encounter_deck': [], 'area_processing': [],
                'area_revealing': [],
            },
            'prompt': {
                'revision': 4, 'ability_type': 'HeroAction',
                'event_name': 'WhenPlayerInTurn', 'prompt_text': 'Act',
                'show_cancel': True,
                'options': [{
                    'id': 31, 'name': 'Attack', 'bind_id': 1,
                    'all_legal_targets': [9], 'target_num_range': [1, 1],
                    'target_payment': {
                        '9': {'cost': '1', 'rule': [],
                              'payment': [{'22': 'Y'}]},
                    },
                    'failure_reason': '', 'select_rule': '',
                }],
            },
        }

        compact = _compact_snapshot(snapshot)
        option = compact['prompt']['options'][0]
        self.assertEqual(option['source'], 'Groot')
        self.assertEqual(option['legal_targets'][0]['name'], 'Klaw')
        self.assertEqual(
            option['payments']['9']['candidates'][0],
            {'effect_id': 22, 'resource': 'Y', 'card_id': 2, 'card': 'Energy'},
        )


class HeadlessAgentFastPathTests(unittest.TestCase):

    def test_agent_wait_is_bounded_and_uses_fast_default(self):
        self.assertEqual(GameServerAgent._clamp_wait_ms(None, 2000), 2000)
        self.assertEqual(GameServerAgent._clamp_wait_ms(-1), 0)
        self.assertEqual(GameServerAgent._clamp_wait_ms(60000), 30000)

    def test_act_returns_the_next_prompt_without_a_fixed_wait(self):
        class FakeManager:
            def __init__(self):
                self.asking_players = [0]
                self.ask_revisions = [3, 0, 0, 0]
                self.controllers = [
                    SimpleNamespace(game=SimpleNamespace(world=None)),
                ]
                self.ask_options = {
                    0: SimpleNamespace(
                        options_json=json.dumps([{'id': 17}]),
                        show_cancel=True,
                    ),
                }

            def WhenInput(self, command, player_id):
                self.command = json.loads(command)
                self.ask_revisions[player_id] += 1

        class FakeRequest:
            async def json(self):
                return {
                    'player_id': 0,
                    'revision': 3,
                    'effect_id': 17,
                    'targets': [],
                    'resources': [],
                }

        server = object.__new__(GameServerAgent)
        server.device_manager = FakeManager()
        server._snapshot = lambda player_id: {
            'status': 'awaiting_input',
            'player_id': player_id,
            'prompt_revision': 4,
        }

        response = asyncio.run(asyncio.wait_for(server.act(FakeRequest()), 0.1))
        payload = json.loads(response.body)
        self.assertEqual(payload['status'], 'awaiting_input')
        self.assertEqual(server.device_manager.command['id'], 17)

    def test_startup_wait_survives_the_brief_idle_transition(self):
        manager = SimpleNamespace(
            asking_players=[],
            ask_revisions=[0, 0, 0, 0],
            controllers=[SimpleNamespace(game=SimpleNamespace(world=None))],
        )
        server = object.__new__(GameServerAgent)
        server.device_manager = manager

        async def wait_through_transition():
            waiting = asyncio.create_task(server._wait_for_agent_state(
                0,
                wait_ms=100,
                since_revision=0,
                decision_only=True,
            ))
            await asyncio.sleep(0.01)
            self.assertFalse(waiting.done())
            manager.ask_revisions[0] = 1
            manager.asking_players.append(0)
            await asyncio.wait_for(waiting, 0.1)

        asyncio.run(wait_through_transition())

    def test_mcp_act_is_one_round_trip_and_returns_compact_state(self):
        snapshot = {
            'status': 'awaiting_input',
            'game_id': 4,
            'step': 9,
            'outcome': None,
            'recent_log': [],
            'world': {'players': []},
            'prompt': None,
        }
        with patch.object(
            marvel_lcg_mcp.CLIENT, 'post', return_value=snapshot,
        ) as post:
            result = marvel_lcg_mcp.call_tool('act', {
                'revision': 7,
                'effect_id': 21,
                'targets': [],
                'resources': [],
            })

        self.assertEqual(result['status'], 'awaiting_input')
        request_payload = post.call_args.args[1]
        self.assertEqual(request_payload['wait_ms'], 2000)
        self.assertEqual(post.call_count, 1)


if __name__ == '__main__':
    unittest.main()
