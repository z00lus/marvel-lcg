from datetime import datetime, timedelta, timezone
import os
import tempfile
import unittest

from engine.lib import Json
from engine.marvelcdb.deck_sync import MarvelCdbDeckSync


SPIDER_MAN_TEMPLATE = {
    'version': '0.6.0',
    'name': 'Spider-Man',
    'metadata': {'url': ''},
    'hero': ['01001a,01001b'],
    'hero_deck': [
        '01002',
        '01003', '01003',
        '01004', '01004',
        '01005', '01005', '01005',
        '01006',
        '01007', '01007',
        '01008', '01008',
        '01009', '01009',
    ],
    'set_aside': [],
    'obligations': ['01165'],
    'nemesis_set': ['01166', '01167', '01168', '01168', '01169'],
    'player_deck': ['old-card'],
}


def create_remote_deck(deck_id='1130039'):
    return {
        'id': int(deck_id),
        'name': 'Spider-Man unti Ultron',
        'date_update': '2026-02-23T16:58:54+00:00',
        'hero_code': '01001a',
        'hero_name': 'Spider-Man',
        'slots': {
            '01002': 1,
            '01003': 2,
            '01004': 2,
            '01005': 3,
            '01006': 1,
            '01007': 2,
            '01008': 2,
            '01009': 2,
            '01051': 1,
            '01052': 2,
            '01054': 2,
        },
    }


class TestMarvelCdbDeckSync(unittest.TestCase):

    def test_parse_deck_ids_normalizes_and_deduplicates(self):
        self.assertEqual(
            MarvelCdbDeckSync.ParseDeckIds('1130039, 01130039,,1143133'),
            ['1130039', '1143133'],
        )

        with self.assertRaisesRegex(ValueError, 'Invalid MarvelCDB deck ID'):
            MarvelCdbDeckSync.ParseDeckIds('1130039,deck-name')

    def test_convert_deck_keeps_identity_template_and_replaces_player_cards(self):
        converted = MarvelCdbDeckSync.ConvertDeck(
            create_remote_deck(),
            SPIDER_MAN_TEMPLATE,
        )

        self.assertEqual(converted['name'], 'Spider-Man')
        self.assertEqual(converted['deck_name'], 'Spider-Man unti Ultron')
        self.assertEqual(converted['hero_deck'], SPIDER_MAN_TEMPLATE['hero_deck'])
        self.assertEqual(
            converted['player_deck'],
            ['01051', '01052', '01052', '01054', '01054'],
        )
        self.assertEqual(converted['metadata']['marvelcdb_id'], '1130039')
        self.assertEqual(SPIDER_MAN_TEMPLATE['player_deck'], ['old-card'])

    def test_double_sided_hero_card_uses_unsuffixed_marvelcdb_code(self):
        template = {
            **SPIDER_MAN_TEMPLATE,
            'hero_deck': ['26002a,26002b'],
        }
        remote = create_remote_deck()
        remote['slots'] = {'26002': 1, '01051': 2}

        converted = MarvelCdbDeckSync.ConvertDeck(remote, template)

        self.assertEqual(converted['player_deck'], ['01051', '01051'])

    def test_sync_writes_engine_deck_and_persists_schedule(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            starter_folder = os.path.join(temp_folder, 'starter')
            user_folder = os.path.join(temp_folder, 'user-decks')
            state_file = os.path.join(user_folder, '.sync-state.json')
            os.makedirs(starter_folder)
            Json.Save(
                SPIDER_MAN_TEMPLATE,
                os.path.join(starter_folder, 'spider_man.json'),
            )
            service = MarvelCdbDeckSync(
                user_deck_folder=user_folder,
                state_file=state_file,
                starter_deck_folder=starter_folder,
                fetch_deck=lambda deck_id: create_remote_deck(deck_id),
            )

            result = service.SyncDecks('1130039')

            self.assertTrue(result['ok'])
            self.assertEqual(result['synced'][0]['name'], 'Spider-Man unti Ultron')
            output = MarvelCdbDeckSync._read_json(
                os.path.join(user_folder, '1130039.json'),
            )
            self.assertEqual(output['deck_name'], 'Spider-Man unti Ultron')
            self.assertEqual(output['name'], 'Spider-Man')
            state = service.GetStatus()
            self.assertEqual(state['deck_ids'], ['1130039'])
            self.assertTrue(state['last_sync'])

    def test_unsupported_hero_is_reported_without_writing_a_deck(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            starter_folder = os.path.join(temp_folder, 'starter')
            user_folder = os.path.join(temp_folder, 'user-decks')
            state_file = os.path.join(user_folder, '.sync-state.json')
            os.makedirs(starter_folder)
            Json.Save(
                SPIDER_MAN_TEMPLATE,
                os.path.join(starter_folder, 'spider_man.json'),
            )
            remote = create_remote_deck()
            remote['hero_code'] = '99999a'
            remote['hero_name'] = 'Unimplemented Hero'
            service = MarvelCdbDeckSync(
                user_deck_folder=user_folder,
                state_file=state_file,
                starter_deck_folder=starter_folder,
                fetch_deck=lambda deck_id: remote,
            )

            result = service.SyncDecks('1130039')

            self.assertFalse(result['ok'])
            self.assertIn('has no starter deck', result['errors'][0]['error'])
            self.assertFalse(os.path.exists(os.path.join(user_folder, '1130039.json')))

    def test_daily_schedule_is_due_after_interval(self):
        service = MarvelCdbDeckSync(interval_seconds=24 * 60 * 60)
        recent = {
            'deck_ids': ['1130039'],
            'last_sync': datetime.now(timezone.utc).isoformat(),
        }
        old = {
            'deck_ids': ['1130039'],
            'last_sync': (
                datetime.now(timezone.utc) - timedelta(days=2)
            ).isoformat(),
        }

        remaining = service._seconds_until_sync(recent)
        self.assertIsNotNone(remaining)
        self.assertGreater(remaining, 23 * 60 * 60)
        self.assertEqual(service._seconds_until_sync(old), 0)

    def test_periodic_worker_stops_cleanly_without_configured_decks(self):
        with tempfile.TemporaryDirectory() as temp_folder:
            service = MarvelCdbDeckSync(
                user_deck_folder=temp_folder,
                state_file=os.path.join(temp_folder, '.sync-state.json'),
                starter_deck_folder=temp_folder,
                fetch_deck=lambda deck_id: create_remote_deck(deck_id),
            )

            service.Start()
            service.Stop()

            self.assertIsNotNone(service._thread)
            self.assertFalse(service._thread.is_alive())


if __name__ == '__main__':
    unittest.main()
