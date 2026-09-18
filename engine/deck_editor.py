"""Local deck editing and Rules Reference 1.8 construction checks.

Only player_deck is editable. Identity packages come from the installed starter
templates, never from HTTP input. Play restrictions (e.g. 'play only if Mystic')
are deliberately not confused with deck construction restrictions.
"""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
import os
from pathlib import Path
import re
import tempfile
import threading
from uuid import uuid4

from cards.database import CardsDB
from engine.lib import Json


ASPECTS = ('Aggression', 'Justice', 'Leadership', 'Protection', "'Pool")
PLAYER_TYPES = {'Ally', 'Event', 'Resource', 'Support', 'Upgrade', 'PlayerSideScheme'}


class DeckEditor:
    _save_lock = threading.Lock()

    def __init__(self, starter_folder, user_folder):
        self.folders = {'starter': Path(starter_folder), 'user': Path(user_folder)}

    def _path(self, source, deck_id):
        if not isinstance(source, str) or source not in self.folders or not isinstance(deck_id, str) or not re.fullmatch(r'[\w-]+', deck_id):
            raise ValueError('Choose a local deck.')
        folder = self.folders[source].resolve()
        path = folder / (deck_id + '.json')
        if path.resolve().parent != folder or path.is_symlink():
            raise ValueError('Invalid deck path.')
        return path

    @staticmethod
    def _read(path):
        try:
            return Json.Loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise ValueError('This deck could not be loaded.') from exc

    @staticmethod
    def _revision(deck):
        return hashlib.sha256(json.dumps(deck, sort_keys=True).encode()).hexdigest()

    def _load(self, source, deck_id):
        original = self._read(self._path(source, deck_id))
        for path in sorted(self.folders['starter'].glob('*.json')):
            template = self._read(path)
            if template.get('hero') == original.get('hero'):
                deck = deepcopy(template)
                deck['player_deck'] = original.get('player_deck', [])
                deck['deck_name'] = original.get('deck_name', original['name'])
                return original, deck
        raise ValueError('No installed identity package matches this deck.')

    @staticmethod
    def _paper(card_id):
        paper = CardsDB.papers.get(card_id.split(',')[0])
        if paper is None:
            raise ValueError(f'Unknown card: {card_id}')
        return paper

    @staticmethod
    def _classes(paper):
        return set(paper.desc.get('Class', '').split(';'))

    @classmethod
    def _player_card(cls, paper):
        return paper.type in PLAYER_TYPES and cls._classes(paper) <= set(ASPECTS) | {'Basic'}

    @classmethod
    def _catalog(cls):
        # Reprints share a single search result; existing decks may retain their
        # original printing. Limits below use titles, not printing identifiers.
        return [p for key, p in CardsDB.papers.items()
                if cls._player_card(p) and key not in CardsDB.full_link_cards]

    @classmethod
    def _identities(cls, deck):
        return [cls._paper(face) for card in deck['hero'] for face in card.split(',')]

    @classmethod
    def _hero(cls, deck):
        return deck['hero'][0].split(',')[0].rstrip('abc')

    @classmethod
    def _aspect_count(cls, deck):
        return {'04031': 2, '21031': 4}.get(cls._hero(deck), 1)

    @classmethod
    def _off_aspect(cls, deck, paper):
        traits = {trait.upper() for trait in paper.traits}
        hero = cls._hero(deck)
        return (
            hero == '18001' and paper.type == 'Event' and bool(traits & {'ATTACK', 'THWART'}) or
            hero == '33001' and paper.type == 'Ally' and 'X-MEN' in traits or
            hero == '40001' and paper.type == 'PlayerSideScheme' or
            hero == '50001' and paper.type == 'Support' and bool(traits & {'S.H.I.E.L.D.', 'S.H.I.E.L.D'}) or
            hero == '58001' and paper.type == 'Event' and 'Y' in paper.desc.get('RES', '')
        )

    @classmethod
    def _allowed(cls, deck, paper, aspects):
        if not cls._player_card(paper):
            return 'Only aspect and basic player cards can be added.'
        team = paper.desc.get('TeamUp', '')
        if team:
            names = {p.name for p in cls._identities(deck)}
            # A slash qualifies a character by both hero and alter-ego names.
            if not any(set(member.split('/')) <= names for member in team.split(';')):
                return 'Team-up requires one of its named identities.'
        if not cls._classes(paper) & (set(aspects) | {'Basic'}) and not cls._off_aspect(deck, paper):
            return 'This card does not belong to your chosen aspect(s).'
        return ''

    @staticmethod
    def _unique_match(left, right):
        titles, aliases = left
        other_titles, other_aliases = right
        if not aliases and not other_aliases:
            return bool(titles & other_titles)
        return bool(aliases & (other_titles | other_aliases) or other_aliases & (titles | aliases))

    @classmethod
    def _unique_key(cls, paper):
        return ({paper.name}, {paper.subtitle} if paper.subtitle else set())

    @classmethod
    def _identity_key(cls, deck):
        identities = cls._identities(deck)
        return ({p.name for p in identities if p.type == 'Hero'},
                {p.name for p in identities if p.type == 'AlterEgo'})

    @classmethod
    def _limit(cls, deck, paper):
        printed = paper.desc.get('MaxPerDeck')
        match = re.search(r'(?:Max|Limit)\s+(\d+)\s+per deck', paper.text, re.I)
        limit = int(printed) if printed else int(match[1]) if match else 3
        return min(limit, 1) if cls._hero(deck) == '21031' and cls._player_card(paper) else limit

    @classmethod
    def _size(cls, papers):
        return sum(not p.desc.get('Permanent') for p in papers)

    @classmethod
    def _addition_error(cls, deck, paper, aspects, existing):
        reason = cls._allowed(deck, paper, aspects)
        if reason:
            return reason
        if cls._size(existing + [paper]) > 50:
            return 'The deck already contains 50 cards.'
        matching = [p for p in existing if p.name == paper.name and
                    (not paper.is_unique or p.subtitle == paper.subtitle)]
        if len(matching) >= cls._limit(deck, paper):
            return f'Maximum {cls._limit(deck, paper)} copies of {paper.name}.'
        if paper.is_unique:
            key = cls._unique_key(paper)
            if cls._unique_match(key, cls._identity_key(deck)) or any(
                p.is_unique and cls._unique_match(key, cls._unique_key(p)) for p in existing
            ):
                return 'A matching unique character/card is already in this deck or is your identity.'
        outside = [p for p in existing + [paper] if cls._player_card(p) and
                   not cls._classes(p) & (set(aspects) | {'Basic'})]
        if cls._hero(deck) == '18001' and len(outside) > 6:
            return 'Gamora may include at most 6 off-aspect attack/thwart events.'
        if cls._hero(deck) == '50001' and len({p.name for p in outside}) > 3:
            return 'Maria Hill may include at most 3 different off-aspect S.H.I.E.L.D. supports.'
        return ''

    @classmethod
    def _infer_aspects(cls, deck):
        players = [cls._paper(card) for card in deck['player_deck']]
        options = list(combinations(ASPECTS, cls._aspect_count(deck)))
        def score(aspects):
            errors = sum(bool(cls._allowed(deck, p, aspects)) for p in players)
            covered = sum(bool(cls._classes(p) & set(aspects)) for p in players)
            return errors, -covered
        return list(min(options, key=score))

    @classmethod
    def validate(cls, deck, player_deck, aspects):
        if not isinstance(player_deck, list) or len(player_deck) > 100 or any(
            not isinstance(card, str) or card not in CardsDB.papers for card in player_deck
        ):
            raise ValueError('Expected a list of known player card IDs (maximum 100).')
        if not isinstance(aspects, list) or any(a not in ASPECTS for a in aspects) or len(set(aspects)) != len(aspects):
            raise ValueError('Choose valid, distinct aspects.')
        required = cls._aspect_count(deck)
        issues = []
        if len(aspects) != required:
            issues.append(f'Choose exactly {required} aspect(s).')
        signatures = [cls._paper(card) for card in deck['hero_deck']]
        existing = list(signatures)
        for card in player_deck:
            paper = cls._paper(card)
            reason = cls._addition_error(deck, paper, aspects, existing)
            if reason:
                issues.append(f'{paper.name}: {reason}')
            existing.append(paper)
        size = cls._size(existing)
        if not 40 <= size <= 50:
            issues.append(f'Deck size must be 40–50 cards; currently {size}. Permanent cards are not counted.')
        counts = {a: sum(a in cls._classes(p) for p in existing) for a in aspects}
        if required > 1 and len(set(counts.values())) > 1:
            issues.append('Chosen aspects must contain equal numbers of cards (including signature cards): ' +
                          ', '.join(f'{a}: {n}' for a, n in counts.items()) + '.')
        catalog = cls._catalog()
        # Include existing reprints so their '+' controls receive the same checks.
        all_cards = {p.card_id: p for p in catalog + existing}
        blocked = {key: cls._addition_error(deck, p, aspects, existing) for key, p in all_cards.items()}
        return {'legal': not issues, 'issues': list(dict.fromkeys(issues)), 'size': size,
                'aspect_counts': counts, 'blocked': blocked}

    def load(self, source, deck_id):
        original, deck = self._load(source, deck_id)
        metadata = original.get('metadata', {})
        aspects = metadata.get('editor_aspects') or self._infer_aspects(deck)
        return {'deck': deck, 'aspects': aspects, 'aspect_count': self._aspect_count(deck),
                'revision': self._revision(original),
                'copy_on_save': source == 'starter' or not metadata.get('local_editor'),
                'catalog': [asdict(p) for p in self._catalog()],
                'validation': self.validate(deck, deck['player_deck'], aspects)}

    def check(self, source, deck_id, player_deck, aspects):
        _, deck = self._load(source, deck_id)
        return self.validate(deck, player_deck, aspects)

    def save(self, source, deck_id, player_deck, aspects, name, revision):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
            raise ValueError('Enter a deck name of 1–100 characters.')
        with self._save_lock:
            original, deck = self._load(source, deck_id)
            if revision != self._revision(original):
                raise ValueError('This deck changed since you opened it. Reload it before saving.')
            result = self.validate(deck, player_deck, aspects)
            if not result['legal']:
                raise ValueError(' '.join(result['issues']))
            old_meta = original.get('metadata', {})
            editable = source == 'user' and old_meta.get('local_editor') is True
            target_id = deck_id if editable else 'local-' + uuid4().hex
            deck['player_deck'] = list(player_deck)
            deck['deck_name'] = name.strip()
            now = datetime.now(timezone.utc).isoformat()
            deck['metadata'] = {'local_editor': True, 'editor_aspects': list(aspects),
                                'local_created_at': old_meta.get('local_created_at', now) if editable else now,
                                'local_updated_at': now}
            target = self._path('user', target_id)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                                 prefix='.editor-', suffix='.tmp', delete=False) as stream:
                    temporary = stream.name
                    json.dump(deck, stream, ensure_ascii=False, indent=4)
                    stream.write('\n')
                os.replace(temporary, target)
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)
            return {'id': target_id, 'deck': deck, 'revision': self._revision(deck)}
