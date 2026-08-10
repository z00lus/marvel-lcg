import json
import os
import tempfile
import unittest
from unittest.mock import patch

from engine.lib import Json
from engine.marvelcdb.deck_sync import MarvelCdbDeckSync

from unit_test.test_marvelcdb_sync import SPIDER_MAN_TEMPLATE, create_remote_deck


class FakeResponse:
    """Minimal stand-in for the object urlopen yields as a context manager."""

    def __init__(self, payload: str) -> None:
        self._payload = payload.encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._payload


def write_starter_template(folder: str) -> None:
    path = os.path.join(folder, 'spider_man.json')
    with open(path, 'w', encoding='utf-8') as file:
        file.write(Json.Dumps(SPIDER_MAN_TEMPLATE, indent=4))


class TestParseDeckRef(unittest.TestCase):

    def test_bare_id_leaves_the_kind_unknown(self):
        # A number alone does not say which endpoint holds it, so both must be
        # tried. Reporting a kind here would make the fallback unreachable.
        self.assertEqual(MarvelCdbDeckSync.ParseDeckRef('63988'), (None, '63988'))
        self.assertEqual(MarvelCdbDeckSync.ParseDeckRef(' 063988 '), (None, '63988'))

    def test_urls_identify_their_kind(self):
        cases = [
            ('https://marvelcdb.com/decklist/view/63988/the-defense-rests-1.0',
             ('decklist', '63988')),
            ('https://marvelcdb.com/deck/view/12345', ('deck', '12345')),
            ('https://marvelcdb.com/deck/edit/12345', ('deck', '12345')),
            ('https://marvelcdb.com/api/public/decklist/63988.json',
             ('decklist', '63988')),
            ('marvelcdb.com/DECKLIST/VIEW/63988', ('decklist', '63988')),
        ]
        for reference, expected in cases:
            with self.subTest(reference=reference):
                self.assertEqual(MarvelCdbDeckSync.ParseDeckRef(reference), expected)

    def test_rejects_nonsense(self):
        for reference in ['', '   ', 'deck-name', 'https://example.com/deck/view/1']:
            with self.subTest(reference=reference):
                with self.assertRaises(ValueError):
                    MarvelCdbDeckSync.ParseDeckRef(reference)

    def test_parse_deck_ids_accepts_links(self):
        # The Settings sync box gains URL support for free by sharing the parser.
        self.assertEqual(
            MarvelCdbDeckSync.ParseDeckIds(
                'https://marvelcdb.com/decklist/view/63988/slug,12345'
            ),
            ['63988', '12345'],
        )


class TestFetchFallback(unittest.TestCase):

    def test_html_body_is_a_miss_not_a_crash(self):
        # MarvelCDB answers a miss with HTTP 200 and an HTML page. Treating that
        # as a hard error is what made a mistyped ID surface as JSONDecodeError.
        requested = []

        def fake_urlopen(request, timeout=None):
            requested.append(request.full_url)
            if 'api/public/deck/' in request.full_url:
                return FakeResponse('<!DOCTYPE html><html>Deckbuilder</html>')
            return FakeResponse(json.dumps(create_remote_deck('63988')))

        with patch('engine.marvelcdb.deck_sync.urlopen', fake_urlopen):
            deck = MarvelCdbDeckSync.FetchDeckRef(None, '63988')

        self.assertEqual(deck['id'], 63988)
        self.assertEqual(deck['marvelcdb_kind'], 'decklist')
        self.assertEqual(len(requested), 2, 'should fall through to the decklist endpoint')

    def test_known_kind_does_not_probe_the_other_endpoint(self):
        requested = []

        def fake_urlopen(request, timeout=None):
            requested.append(request.full_url)
            return FakeResponse(json.dumps(create_remote_deck('63988')))

        with patch('engine.marvelcdb.deck_sync.urlopen', fake_urlopen):
            deck = MarvelCdbDeckSync.FetchDeckRef('decklist', '63988')

        self.assertEqual(deck['marvelcdb_kind'], 'decklist')
        self.assertEqual(len(requested), 1)
        self.assertIn('api/public/decklist/63988', requested[0])

    def test_missing_everywhere_names_both_endpoints(self):
        def fake_urlopen(request, timeout=None):
            return FakeResponse('<!DOCTYPE html>')

        with patch('engine.marvelcdb.deck_sync.urlopen', fake_urlopen):
            with self.assertRaisesRegex(ValueError, 'deck or decklist'):
                MarvelCdbDeckSync.FetchDeckRef(None, '999999')


class TestResolveDeck(unittest.TestCase):

    def build_service(self, starter_folder, campaign_folder, remote=None):
        return MarvelCdbDeckSync(
            user_deck_folder=os.path.join(campaign_folder, 'user'),
            campaign_deck_folder=campaign_folder,
            state_file=os.path.join(campaign_folder, '.state.json'),
            starter_deck_folder=starter_folder,
            fetch_deck_ref=lambda kind, deck_id: dict(
                remote or create_remote_deck(deck_id),
                marvelcdb_kind=kind or 'deck',
            ),
        )

    def test_resolve_converts_without_writing_anything(self):
        with tempfile.TemporaryDirectory() as folder:
            starter = os.path.join(folder, 'starter')
            campaign = os.path.join(folder, 'campaign')
            os.makedirs(starter)
            os.makedirs(campaign)
            write_starter_template(starter)

            service = self.build_service(starter, campaign)
            deck = service.ResolveDeck('https://marvelcdb.com/decklist/view/63988/slug')

            # The signature cards come from the template, the rest from MarvelCDB.
            self.assertEqual(deck['name'], 'Spider-Man')
            self.assertEqual(deck['deck_name'], 'Spider-Man unti Ultron')
            self.assertEqual(deck['nemesis_set'], SPIDER_MAN_TEMPLATE['nemesis_set'])
            self.assertNotIn('old-card', deck['player_deck'])
            self.assertIn('01051', deck['player_deck'])
            self.assertEqual(deck['metadata']['marvelcdb_kind'], 'decklist')
            self.assertEqual(
                deck['metadata']['url'],
                'https://marvelcdb.com/decklist/view/63988',
            )

            # Resolving is the whole point of not leaving files behind.
            self.assertEqual(os.listdir(campaign), [])

    def test_unknown_hero_is_reported_by_name(self):
        with tempfile.TemporaryDirectory() as folder:
            starter = os.path.join(folder, 'starter')
            campaign = os.path.join(folder, 'campaign')
            os.makedirs(starter)
            os.makedirs(campaign)
            write_starter_template(starter)

            remote = create_remote_deck('63988')
            remote['hero_code'] = '99999a'
            remote['hero_name'] = 'Unimplemented Hero'

            service = self.build_service(starter, campaign, remote=remote)
            with self.assertRaisesRegex(ValueError, 'Unimplemented Hero'):
                service.ResolveDeck('63988')


class TestCampaignDeck(unittest.TestCase):

    def test_saved_deck_is_frozen_until_refreshed(self):
        with tempfile.TemporaryDirectory() as folder:
            starter = os.path.join(folder, 'starter')
            campaign = os.path.join(folder, 'campaign')
            os.makedirs(starter)
            os.makedirs(campaign)
            write_starter_template(starter)

            remote = create_remote_deck('63988')
            service = MarvelCdbDeckSync(
                user_deck_folder=os.path.join(folder, 'user'),
                campaign_deck_folder=campaign,
                state_file=os.path.join(folder, '.state.json'),
                starter_deck_folder=starter,
                fetch_deck_ref=lambda kind, deck_id: dict(remote, marvelcdb_kind='decklist'),
            )

            resolved = service.ResolveDeck(
                'https://marvelcdb.com/decklist/view/63988/slug'
            )
            saved = service.SaveCampaignDeck('mutant_genesis', resolved)
            self.assertEqual(saved['hero_id'], 'mutant_genesis-01001a')

            deck_path = service.CampaignDeckPath(saved['hero_id'])
            self.assertTrue(os.path.exists(deck_path))

            # The netdeck changes on MarvelCDB...
            remote['slots'] = dict(remote['slots'])
            remote['slots']['01054'] = 0
            remote['slots']['01055'] = 3

            # ...and the frozen file does not follow it on its own.
            with open(deck_path, encoding='utf-8') as file:
                on_disk = json.load(file)
            self.assertIn('01054', on_disk['player_deck'])
            self.assertNotIn('01055', on_disk['player_deck'])

            # Only an explicit refresh pulls it in, and it reports the delta:
            # two copies of 01054 removed, three of 01055 added.
            result = service.RefreshCampaignDeck(saved['hero_id'])
            self.assertEqual(result['changed'], 5)
            self.assertNotIn('01054', result['deck']['player_deck'])
            self.assertIn('01055', result['deck']['player_deck'])

    def test_refresh_refuses_a_hero_swap(self):
        with tempfile.TemporaryDirectory() as folder:
            starter = os.path.join(folder, 'starter')
            campaign = os.path.join(folder, 'campaign')
            os.makedirs(starter)
            os.makedirs(campaign)
            write_starter_template(starter)

            other_template = dict(SPIDER_MAN_TEMPLATE)
            other_template['name'] = 'Captain America'
            other_template['hero'] = ['01029a,01029b']
            with open(os.path.join(starter, 'captain_america.json'), 'w',
                      encoding='utf-8') as file:
                file.write(Json.Dumps(other_template, indent=4))

            remote = create_remote_deck('63988')
            service = MarvelCdbDeckSync(
                user_deck_folder=os.path.join(folder, 'user'),
                campaign_deck_folder=campaign,
                state_file=os.path.join(folder, '.state.json'),
                starter_deck_folder=starter,
                fetch_deck_ref=lambda kind, deck_id: dict(remote, marvelcdb_kind='decklist'),
            )

            saved = service.SaveCampaignDeck('mutant_genesis', service.ResolveDeck('63988'))

            # The MarvelCDB deck is rebuilt around a different hero entirely.
            remote['hero_code'] = '01029a'
            remote['hero_name'] = 'Captain America'

            with self.assertRaisesRegex(ValueError, 'cannot change hero mid-run'):
                service.RefreshCampaignDeck(saved['hero_id'])

    def test_refresh_rejects_a_deck_with_no_origin(self):
        with tempfile.TemporaryDirectory() as folder:
            campaign = os.path.join(folder, 'campaign')
            os.makedirs(campaign)
            service = MarvelCdbDeckSync(
                user_deck_folder=os.path.join(folder, 'user'),
                campaign_deck_folder=campaign,
                state_file=os.path.join(folder, '.state.json'),
                starter_deck_folder=os.path.join(folder, 'starter'),
            )

            hand_made = dict(SPIDER_MAN_TEMPLATE)
            with open(service.CampaignDeckPath('handmade'), 'w', encoding='utf-8') as file:
                file.write(Json.Dumps(hand_made, indent=4))

            with self.assertRaisesRegex(ValueError, 'did not come from MarvelCDB'):
                service.RefreshCampaignDeck('handmade')


if __name__ == '__main__':
    unittest.main()
