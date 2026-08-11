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

    def test_parse_deck_refs_keeps_the_kind_a_url_declared(self):
        # The Settings sync box gains URL support for free by sharing the
        # parser, but it must store the kind too: normalising to a bare ID here
        # is what let a decklist URL later sync deck/<same id>.
        self.assertEqual(
            MarvelCdbDeckSync.ParseDeckRefs(
                'https://marvelcdb.com/decklist/view/63988/slug,12345'
            ),
            ['https://marvelcdb.com/decklist/view/63988', '12345'],
        )

    def test_canonical_refs_round_trip(self):
        # ParseDeckRefs stores what CanonicalRef renders, and the sync loop
        # parses it straight back, so the two must be exact inverses.
        for kind, deck_id in [('deck', '123'), ('decklist', '123'), (None, '123')]:
            with self.subTest(kind=kind):
                ref = MarvelCdbDeckSync.CanonicalRef(kind, deck_id)
                self.assertEqual(MarvelCdbDeckSync.ParseDeckRef(ref), (kind, deck_id))
                self.assertEqual(MarvelCdbDeckSync.ParseDeckRefs(ref), [ref])


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

    def test_hero_id_needs_both_halves(self):
        with self.assertRaisesRegex(ValueError, 'both a campaign and a hero'):
            MarvelCdbDeckSync.CampaignDeckHeroId('mutant_genesis', '')
        with self.assertRaisesRegex(ValueError, 'both a campaign and a hero'):
            MarvelCdbDeckSync.CampaignDeckHeroId('', '01001a')
        with self.assertRaisesRegex(ValueError, 'both a campaign and a hero'):
            MarvelCdbDeckSync.CampaignDeckHeroId('   ', '01001a')

        # Non-empty but unusable: nothing survives the alphabet.
        with self.assertRaisesRegex(ValueError, 'Invalid campaign deck name'):
            MarvelCdbDeckSync.CampaignDeckHeroId('...', '///')


class TestCampaignDeckPathTraversal(unittest.TestCase):
    """`hero_id` reaches CampaignDeckPath straight from an HTTP body."""

    HOSTILE = [
        '../../outside',
        '../outside',
        '..',
        'sub/outside',
        'sub\\outside',
        '/etc/passwd',
        '/absolute',
        'C:\\windows\\system32',
        'name.with.dots',
        '-leading-hyphen',
        'trailing-hyphen-',
        'space in name',
        'null\x00byte',
        '',
        '   ',
        '%2e%2e%2foutside',
        'deck\n../outside',
    ]

    def _service(self, folder: str) -> MarvelCdbDeckSync:
        campaign = os.path.join(folder, 'campaign')
        os.makedirs(campaign, exist_ok=True)
        return MarvelCdbDeckSync(
            user_deck_folder=os.path.join(folder, 'user'),
            campaign_deck_folder=campaign,
            state_file=os.path.join(folder, '.state.json'),
            starter_deck_folder=os.path.join(folder, 'starter'),
        )

    def test_hostile_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            service = self._service(folder)
            for hero_id in self.HOSTILE:
                with self.subTest(hero_id=hero_id):
                    with self.assertRaises(ValueError):
                        service.CampaignDeckPath(hero_id)

    def test_refresh_rejects_hostile_ids_before_touching_disk(self):
        """The escape target must survive untouched, not merely be reported.

        Rejecting the path is only half the property. A refresh that validated
        late could still read the outside file and write it back, so assert the
        bytes are unchanged afterwards.
        """
        with tempfile.TemporaryDirectory() as folder:
            service = self._service(folder)

            outside_path = os.path.join(folder, 'outside.json')
            original = Json.Dumps(dict(SPIDER_MAN_TEMPLATE), indent=4)
            with open(outside_path, 'w', encoding='utf-8') as file:
                file.write(original)

            for hero_id in ['../outside', '../../outside', 'sub/../../outside']:
                with self.subTest(hero_id=hero_id):
                    with self.assertRaises(ValueError):
                        service.RefreshCampaignDeck(hero_id)

            with open(outside_path, encoding='utf-8') as file:
                self.assertEqual(file.read(), original)

    def test_generated_ids_are_accepted_and_stay_inside(self):
        """The guard must not reject what CampaignDeckHeroId actually emits."""
        with tempfile.TemporaryDirectory() as folder:
            service = self._service(folder)
            campaign_folder = os.path.realpath(os.path.join(folder, 'campaign'))

            for campaign_id, hero_code in [
                ('mutant_genesis', '01001a'),
                ('The Rise of Red Skull', '01001a'),
                ('sinister-motives', '26002'),
            ]:
                hero_id = MarvelCdbDeckSync.CampaignDeckHeroId(campaign_id, hero_code)
                path = service.CampaignDeckPath(hero_id)
                with self.subTest(hero_id=hero_id):
                    self.assertEqual(os.path.dirname(path), campaign_folder)
                    self.assertTrue(path.endswith('.json'))


class TestSyncPreservesDeckKind(unittest.TestCase):

    @staticmethod
    def _remote(kind: str, name: str) -> dict:
        deck = create_remote_deck('123')
        deck['name'] = name
        deck['marvelcdb_kind'] = kind
        return deck

    def test_a_decklist_url_never_syncs_the_deck_of_the_same_id(self):
        """deck/123 and decklist/123 are different decks that share a number.

        The Settings box stored a parsed URL as a bare ID, so the periodic sync
        probed `deck` first and silently pulled the wrong one.
        """
        with tempfile.TemporaryDirectory() as folder:
            starter = os.path.join(folder, 'starter')
            user = os.path.join(folder, 'user')
            os.makedirs(starter)
            os.makedirs(user)
            write_starter_template(starter)

            bodies = {
                'deck': self._remote('deck', 'Wrong deck'),
                'decklist': self._remote('decklist', 'Right decklist'),
            }
            asked: list = []

            def fetch_ref(kind, deck_id):
                asked.append(kind)
                return bodies[kind or 'deck']

            service = MarvelCdbDeckSync(
                user_deck_folder=user,
                campaign_deck_folder=os.path.join(folder, 'campaign'),
                state_file=os.path.join(folder, '.state.json'),
                starter_deck_folder=starter,
                fetch_deck_ref=fetch_ref,
            )

            result = service.SyncDecks('https://marvelcdb.com/decklist/view/123/slug')

            self.assertEqual(result['errors'], [])
            self.assertEqual(asked, ['decklist'])
            self.assertEqual(result['synced'][0]['name'], 'Right decklist')

            # The kind has to survive the round trip through state, or the next
            # scheduled sync reverts to probing `deck` first.
            with open(os.path.join(folder, '.state.json'), encoding='utf-8') as file:
                state = json.load(file)
            self.assertEqual(
                state['deck_ids'],
                ['https://marvelcdb.com/decklist/view/123'],
            )
            self.assertEqual(
                MarvelCdbDeckSync.ParseDeckRefs(state['deck_ids']),
                ['https://marvelcdb.com/decklist/view/123'],
            )

    def test_a_bare_id_still_probes_both_endpoints(self):
        """Existing sync state holds bare IDs and must keep working."""
        with tempfile.TemporaryDirectory() as folder:
            starter = os.path.join(folder, 'starter')
            user = os.path.join(folder, 'user')
            os.makedirs(starter)
            os.makedirs(user)
            write_starter_template(starter)

            asked: list = []

            def fetch_ref(kind, deck_id):
                asked.append(kind)
                return self._remote('deck', 'Probed deck')

            service = MarvelCdbDeckSync(
                user_deck_folder=user,
                campaign_deck_folder=os.path.join(folder, 'campaign'),
                state_file=os.path.join(folder, '.state.json'),
                starter_deck_folder=starter,
                fetch_deck_ref=fetch_ref,
            )

            result = service.SyncDecks('123')

            self.assertEqual(result['errors'], [])
            self.assertEqual(asked, [None])
            with open(os.path.join(folder, '.state.json'), encoding='utf-8') as file:
                self.assertEqual(json.load(file)['deck_ids'], ['123'])


if __name__ == '__main__':
    unittest.main()
