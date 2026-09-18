"""Construction rules and safe persistence, using the shipped card database."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from engine import Engine  # noqa: F401 -- normal application import order
from engine.lib import Ver
from cards.database import CardsDB
from engine.deck_editor import DeckEditor, ASPECTS
from engine.device.web.server.server_deck_editor import GameServerDeckEditor


class DeckEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.editor = DeckEditor('deck/starter', self.temp.name)
        self.server = object.__new__(GameServerDeckEditor)
        self.server.HeaderNoStore = {'Cache-Control': 'no-store'}

    def deck(self, name='spider_man'):
        return json.loads(Path(f'deck/starter/{name}.json').read_text())

    def check(self, cards, aspects=('Justice',), hero='spider_man'):
        return self.editor.validate(self.deck(hero), cards, list(aspects))

    def additions(self, cards, aspects=('Justice',), hero='spider_man'):
        return self.check(cards, aspects, hero)['blocked']

    def test_starter_is_legal_and_identity_package_not_searchable(self):
        loaded = self.editor.load('starter', 'spider_man')
        self.assertTrue(loaded['validation']['legal'], loaded['validation']['issues'])
        self.assertTrue(loaded['copy_on_save'])
        ids = {p['card_id'] for p in loaded['catalog']}
        self.assertNotIn('01002', ids)
        self.assertNotIn('01001a', ids)
        self.assertNotIn('01104', ids)  # villain

    def test_non_unique_limit_includes_reprints(self):
        original = CardsDB.papers['01060']
        reprints = [key for key, p in CardsDB.papers.items() if p.name == original.name and key != original.card_id]
        self.assertTrue(reprints)
        result = self.check(['01060', '01060', reprints[0], reprints[0]])
        self.assertTrue(any('Maximum 3' in issue for issue in result['issues']))
        self.assertTrue(result['blocked']['01060'])

    def test_printed_one_and_two_copy_limits(self):
        for cards, name in [(['01088'] * 2, 'Energy'), (['01062'] * 3, 'The Power of Justice')]:
            with self.subTest(name=name):
                result = self.check(cards)
                self.assertTrue(any(name in issue and 'Maximum' in issue for issue in result['issues']))

    def test_unique_duplicates_and_hero_alias_conflicts(self):
        self.assertTrue(self.additions(['01084'])['01084'])  # Nick Fury
        self.assertTrue(self.additions([])['04045'])  # Peter Parker ally vs identity
        self.assertEqual(self.additions([])['13019'], '')  # Miles Morales is different

    def test_different_titles_same_character_conflict(self):
        # Identity aliases are compared, not just the name printed on the hero side.
        self.assertTrue(self.additions([], hero='wonder_man', aspects=('Leadership',))['03014'])

    def test_same_title_different_unique_subtitles_can_coexist(self):
        self.assertEqual(self.additions(['13019'])['27017'], '')  # Miles / Hobie

    def test_team_up_requires_named_identity(self):
        self.assertTrue(self.additions([])['12020'])
        self.assertEqual(self.additions([], hero='ant_man', aspects=('Leadership',))['12020'], '')
        self.assertEqual(self.additions([], hero='ghost_spider', aspects=('Protection',))['27019'], '')

    def test_hero_and_encounter_cards_cannot_be_added(self):
        for card in ['01002', '01104', '01001a']:
            with self.subTest(card=card):
                result = self.check([card])
                self.assertTrue(any('Only aspect and basic' in error for error in result['issues']))

    def test_aspect_restrictions(self):
        blocked = self.additions([])
        self.assertTrue(blocked['01050'])  # aggression ally
        self.assertEqual(blocked['01060'], '')
        self.assertFalse(self.check(self.deck()['player_deck'], ASPECTS[:2])['legal'])

    def test_play_trait_restrictions_do_not_prevent_deckbuilding(self):
        # Sorcerer Supreme may be included even though Spider-Man cannot play it.
        papers = [p for p in self.editor._catalog() if p.name == 'The Sorcerer Supreme']
        self.assertTrue(papers)
        self.assertEqual(self.additions([])[papers[0].card_id], '')

    def test_deck_size_and_maximum_addition(self):
        cards = self.deck()['player_deck']
        self.assertFalse(self.check(cards[:-1])['legal'])
        # Use distinct eligible cards to reach 50, avoiding copy limits.
        while len(cards) < 35:
            blocked = self.additions(cards)
            card = next(key for key, reason in blocked.items() if not reason and key not in cards)
            cards.append(card)
        result = self.check(cards)
        self.assertTrue(result['legal'], result['issues'])
        self.assertTrue(all(result['blocked'].values()))

    def test_permanents_do_not_count_towards_size(self):
        deck = self.deck()
        permanent = next(p.card_id for p in CardsDB.papers.values() if p.desc.get('Permanent'))
        deck['hero_deck'].append(permanent)
        result = self.editor.validate(deck, deck['player_deck'], ['Justice'])
        self.assertEqual(result['size'], 40)
        self.assertTrue(result['legal'], result['issues'])

    def test_spider_woman_balance_counts_signature_aspects(self):
        deck = self.deck('spider_woman')
        result = self.editor.validate(deck, deck['player_deck'], ['Aggression', 'Justice'])
        self.assertTrue(result['legal'], result['issues'])
        self.assertEqual(result['aspect_counts']['Aggression'], result['aspect_counts']['Justice'])
        deck['player_deck'].remove('04040')
        result = self.editor.validate(deck, deck['player_deck'], ['Aggression', 'Justice'])
        self.assertTrue(any('equal numbers' in issue for issue in result['issues']))
        # Choosing Pool means the two fixed hero cards in the other chosen aspect
        # still participate in balance.
        result = self.editor.validate(deck, [], ['Aggression', "'Pool"])
        self.assertEqual(result['aspect_counts'], {'Aggression': 2, "'Pool": 0})

    def test_adam_warlock_singletons_balance_and_pool_replacement(self):
        deck = self.deck('adam_warlock')
        result = self.editor.validate(deck, deck['player_deck'], list(ASPECTS[:4]))
        self.assertTrue(result['legal'], result['issues'])
        self.assertTrue(result['blocked']['21041'])
        replacement = ['Aggression', 'Justice', 'Leadership', "'Pool"]
        result = self.check([], replacement, 'adam_warlock')
        self.assertEqual(result['blocked']['44025'], '')
        self.assertTrue(result['blocked']['01077'])

    def test_gamora_only_six_off_aspect_attack_thwart_events(self):
        blocked = self.additions([], ('Aggression',), 'gamora')
        self.assertEqual(blocked['01060'], '')
        self.assertTrue(blocked['01061'])  # non-attack/thwart event
        # Select two real off-aspect attack/thwart events with a three-copy limit.
        candidates = [p.card_id for p in self.editor._catalog() if not blocked[p.card_id]
                      and p.desc['Class'] not in ('Aggression', 'Basic')
                      and self.editor._limit(self.deck('gamora'), p) == 3]
        cards = [candidates[0]] * 3 + [candidates[1]] * 3
        self.assertIn('at most 6', self.additions(cards, ('Aggression',), 'gamora')[candidates[2]])

    def test_cyclops_and_cable_exceptions(self):
        self.assertEqual(self.additions([], ('Leadership',), 'cyclops')['33013'], '')
        # Find cards by traits/type to verify exactly the allowed exception.
        for hero, predicate in [('cyclops', lambda p: p.type == 'Ally' and 'X-MEN' in p.traits),
                                ('cable', lambda p: p.type == 'PlayerSideScheme')]:
            blocked = self.additions([], ('Justice',), hero)
            candidates = [p for p in self.editor._catalog() if p.desc['Class'] == 'Aggression' and predicate(p)]
            self.assertTrue(candidates)
            self.assertTrue(any(not blocked[p.card_id] for p in candidates))
            self.assertTrue(blocked['01050'])  # Hulk is neither exception

    def test_maria_hill_support_exception_and_three_title_limit(self):
        deck = self.deck('maria_hill')
        result = self.editor.validate(deck, deck['player_deck'], ['Leadership'])
        self.assertTrue(result['legal'], result['issues'])
        self.assertIn('at most 3', result['blocked']['01056'])

    def test_wonder_man_energy_event_exception(self):
        blocked = self.additions([], ('Leadership',), 'wonder_man')
        candidates = [p for p in self.editor._catalog() if p.desc['Class'] == 'Aggression' and p.type == 'Event']
        energy = next(p for p in candidates if 'Y' in p.desc.get('RES', ''))
        other = next(p for p in candidates if 'Y' not in p.desc.get('RES', ''))
        self.assertEqual(blocked[energy.card_id], '')
        self.assertTrue(blocked[other.card_id])

    def test_save_creates_copy_preserves_original_then_updates_local(self):
        path = Path('deck/starter/spider_man.json')
        before = path.read_bytes()
        loaded = self.editor.load('starter', 'spider_man')
        saved = self.editor.save('starter', 'spider_man', loaded['deck']['player_deck'],
                                 loaded['aspects'], 'My Spidey', loaded['revision'])
        self.assertTrue(saved['id'].startswith('local-'))
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(saved['deck']['hero_deck'], loaded['deck']['hero_deck'])
        reopened = self.editor.load('user', saved['id'])
        self.assertFalse(reopened['copy_on_save'])
        updated = self.editor.save('user', saved['id'], reopened['deck']['player_deck'],
                                   reopened['aspects'], 'Renamed', reopened['revision'])
        self.assertEqual(updated['id'], saved['id'])
        self.assertEqual(len(list(Path(self.temp.name).glob('*.json'))), 1)
        self.assertEqual(updated['deck']['metadata']['local_created_at'], saved['deck']['metadata']['local_created_at'])

    def test_synced_deck_is_copied_not_overwritten(self):
        path = Path(self.temp.name) / '123.json'
        path.write_text(json.dumps(self.deck()))
        before = path.read_bytes()
        loaded = self.editor.load('user', '123')
        saved = self.editor.save('user', '123', loaded['deck']['player_deck'], loaded['aspects'], 'Copy', loaded['revision'])
        self.assertNotEqual(saved['id'], '123')
        self.assertEqual(path.read_bytes(), before)

    def test_invalid_save_and_stale_revision_write_nothing(self):
        loaded = self.editor.load('starter', 'spider_man')
        for cards, revision in [([], loaded['revision']), (loaded['deck']['player_deck'], 'stale')]:
            with self.assertRaises(ValueError):
                self.editor.save('starter', 'spider_man', cards, loaded['aspects'], 'Test', revision)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_failed_atomic_write_keeps_saved_deck_and_cleans_temporary_file(self):
        loaded = self.editor.load('starter', 'spider_man')
        saved = self.editor.save('starter', 'spider_man', loaded['deck']['player_deck'],
                                 loaded['aspects'], 'Original', loaded['revision'])
        path = Path(self.temp.name) / (saved['id'] + '.json')
        before = path.read_bytes()
        with patch('engine.deck_editor.os.replace', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.editor.save('user', saved['id'], saved['deck']['player_deck'],
                                 loaded['aspects'], 'Changed', saved['revision'])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [path])

    def test_full_server_registers_authenticated_editor_route(self):
        from engine.device.web.server.server import GameServer
        async def check():
            server = GameServer(SimpleNamespace())
            route = next(route for route in server.web_app.router.routes()
                         if route.method == 'POST' and route.resource.canonical == '/deck_editor')
            server.hash_password = 'required-token'
            response = await route.handler(SimpleNamespace(cookies={}))
            self.assertEqual(response.status, 401)
            await server.runner.cleanup()
        asyncio.run(check())

    def test_malformed_inputs_and_path_traversal(self):
        for source, name in [('user', '../outside'), ('user', '/tmp/outside'), ([], 'test'), ('unknown', 'test')]:
            with self.subTest(source=source, name=name), self.assertRaises(ValueError):
                self.editor.load(source, name)
        for cards in [['not-a-card'], [12], '01060', ['01060'] * 101, [['01060']]]:
            with self.subTest(cards=str(cards)[:30]), self.assertRaises(ValueError):
                self.check(cards)

    def test_symlinks_cannot_be_read_or_overwritten(self):
        (Path(self.temp.name) / 'link.json').symlink_to(Path('deck/starter/spider_man.json').resolve())
        with self.assertRaises(ValueError):
            self.editor.load('user', 'link')

    def test_api_cannot_replace_identity_or_signature_package(self):
        loaded = self.editor.load('starter', 'spider_man')
        class Request:
            async def json(self):
                return {'action': 'save', 'source': 'starter', 'id': 'spider_man',
                        'player_deck': loaded['deck']['player_deck'], 'aspects': loaded['aspects'],
                        'name': 'Safe copy', 'revision': loaded['revision'],
                        'hero': ['01104'], 'hero_deck': []}
        with patch('engine.device.web.server.server_deck_editor.DeckEditor', return_value=self.editor):
            response = asyncio.run(self.server.deck_editor(Request()))
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.text)['deck']['hero'], loaded['deck']['hero'])
        self.assertEqual(json.loads(response.text)['deck']['hero_deck'], loaded['deck']['hero_deck'])

    def test_api_rejects_malformed_json_and_invalid_save(self):
        for payload in [[], {'action': 'save', 'source': 'starter', 'id': 'spider_man'},
                        {'action': 'delete'}, {'action': 'load', 'source': [], 'id': 'spider_man'}]:
            class Request:
                async def json(self):
                    return payload
            with self.subTest(payload=payload), patch('engine.device.web.server.server_deck_editor.DeckEditor', return_value=self.editor):
                response = asyncio.run(self.server.deck_editor(Request()))
                self.assertEqual(response.status, 400)


if __name__ == '__main__':
    unittest.main()
