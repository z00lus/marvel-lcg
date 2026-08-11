import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from engine import Engine  # noqa: F401 - preserve normal application import order
from game.game import Game
from game.game_run.campaign_progress import (
    CampaignProgressConflict,
    CampaignProgressStore,
)


class CampaignProgressStoreTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = str(Path(self.temp_dir.name) / 'campaign.json')
        self.store = CampaignProgressStore(self.file_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def campaign(
        campaign_id='rise_of_red_skull',
        scenario_index=0,
        hero_id='spider_man',
        *,
        completed=False,
        campaign_log=None,
    ):
        return {
            'version': 1,
            'campaignId': campaign_id,
            'scenarioIndex': scenario_index,
            'heroId': hero_id,
            'campaignLog': campaign_log or {},
            'completed': completed,
            'updatedAt': '2026-08-11T10:00:00+00:00',
        }

    @staticmethod
    def active_run(
        campaign_id='rise_of_red_skull',
        scenario_id='crossbones',
        scenario_name='Crossbones',
        scenario_index=0,
    ):
        return {
            'version': 1,
            'campaignId': campaign_id,
            'scenarioId': scenario_id,
            'scenarioName': scenario_name,
            'scenarioIndex': scenario_index,
        }

    def start_request(self, *, campaign=None, active_run=None, replace=False):
        return {
            'campaign': campaign or self.campaign(),
            'activeRun': active_run or self.active_run(),
            'replace': replace,
        }

    def test_progress_survives_a_new_store_instance(self):
        self.store.Start(self.start_request())

        restored = CampaignProgressStore(self.file_path).Load()

        self.assertIsNotNone(restored)
        self.assertEqual(restored['campaign']['campaignId'], 'rise_of_red_skull')
        self.assertEqual(restored['campaign']['heroId'], 'spider_man')
        self.assertEqual(restored['activeRun']['scenarioId'], 'crossbones')

    def test_new_campaign_requires_explicit_replacement(self):
        self.store.Start(self.start_request())
        replacement = self.start_request(
            campaign=self.campaign(
                campaign_id='sinister_motives',
                hero_id='daredevil',
            ),
            active_run=self.active_run(
                campaign_id='sinister_motives',
                scenario_id='sandman',
                scenario_name='Sandman',
            ),
        )

        with self.assertRaises(CampaignProgressConflict):
            self.store.Start(replacement)
        self.assertEqual(
            self.store.Load()['campaign']['campaignId'],
            'rise_of_red_skull',
        )

        replacement['replace'] = True
        self.store.Start(replacement)
        self.assertEqual(
            self.store.Load()['campaign']['campaignId'],
            'sinister_motives',
        )

    def test_local_storage_migration_never_overwrites_server_progress(self):
        first, migrated = self.store.Migrate({
            'campaign': self.campaign(),
            'activeRun': None,
        })
        second, migrated_again = self.store.Migrate({
            'campaign': self.campaign(
                campaign_id='sinister_motives',
                hero_id='daredevil',
            ),
            'activeRun': None,
        })

        self.assertTrue(migrated)
        self.assertFalse(migrated_again)
        self.assertEqual(first, second)
        self.assertEqual(second['campaign']['campaignId'], 'rise_of_red_skull')

    def test_defeat_does_not_advance_the_scenario(self):
        self.store.Start(self.start_request())

        result = self.store.AdvanceVerified(
            campaign_id='rise_of_red_skull',
            scenario_name='Crossbones',
            campaign_log={'Player 1 Remaining hit points': '0'},
            game_over=True,
            players_won=False,
            is_replay=False,
        )

        self.assertFalse(result['advanced'])
        self.assertEqual(result['reason'], 'not_victory')
        restored = self.store.Load()
        self.assertEqual(restored['campaign']['scenarioIndex'], 0)
        self.assertIsNotNone(restored['activeRun'])

    def test_victory_advances_exactly_once_and_merges_the_campaign_log(self):
        self.store.Start(self.start_request(
            campaign=self.campaign(campaign_log={'Unspent Units': '2'}),
        ))

        first = self.store.AdvanceVerified(
            campaign_id='rise_of_red_skull',
            scenario_name='Crossbones',
            campaign_log={
                'Unspent Units': '4',
                'Player 1 Remaining hit points': '7',
            },
            game_over=True,
            players_won=True,
            is_replay=False,
        )
        second = self.store.AdvanceVerified(
            campaign_id='rise_of_red_skull',
            scenario_name='Crossbones',
            campaign_log={'Unspent Units': '99'},
            game_over=True,
            players_won=True,
            is_replay=False,
        )

        self.assertTrue(first['advanced'])
        self.assertEqual(first['campaign']['scenarioIndex'], 1)
        self.assertEqual(first['campaign']['campaignLog']['Unspent Units'], '4')
        self.assertEqual(
            first['campaign']['campaignLog']['Player 1 Remaining hit points'],
            '7',
        )
        self.assertFalse(second['advanced'])
        self.assertEqual(second['reason'], 'already_recorded')
        self.assertEqual(second['campaign']['scenarioIndex'], 1)
        self.assertEqual(second['campaign']['campaignLog']['Unspent Units'], '4')

    def test_final_scenario_marks_the_campaign_complete(self):
        campaign = self.campaign(
            campaign_id='rise_of_red_skull',
            scenario_index=4,
        )
        active_run = self.active_run(
            scenario_id='red_skull',
            scenario_name='Red Skull',
            scenario_index=4,
        )
        self.store.Start(self.start_request(
            campaign=campaign,
            active_run=active_run,
        ))

        result = self.store.AdvanceVerified(
            campaign_id='rise_of_red_skull',
            scenario_name='Red Skull',
            campaign_log={},
            game_over=True,
            players_won=True,
            is_replay=False,
        )

        self.assertTrue(result['advanced'])
        self.assertTrue(result['campaign']['completed'])
        self.assertEqual(result['campaign']['scenarioIndex'], 4)

    def test_resumed_game_uses_the_authoritative_server_campaign_log(self):
        self.store.Start(self.start_request(
            campaign=self.campaign(campaign_log={'Unspent Units': '7'}),
        ))
        descriptor = SimpleNamespace(
            campaign_log={'Unspent Units': '1'},
            campaign_progress=self.start_request(
                campaign=self.campaign(campaign_log={'Unspent Units': '1'}),
            ),
        )
        game = Game.__new__(Game)
        game.session = SimpleNamespace(world=None, NewGame=Mock())
        game.controller_manager = SimpleNamespace(
            replay=SimpleNamespace(SetIsReplay=Mock()),
            OnNewGame=Mock(),
        )
        game.campaign_progress = self.store
        game.RemoveActiveSessionFile = Mock()

        game.NewGame(descriptor)

        self.assertEqual(descriptor.campaign_log, {'Unspent Units': '7'})
        game.session.NewGame.assert_called_once_with(descriptor)


if __name__ == '__main__':
    unittest.main()
