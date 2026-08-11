from __future__ import annotations

from collections import Counter
import copy
from datetime import datetime, timedelta, timezone
import json
import os
import re
import threading
from typing import Any, Callable, Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from engine.config import ConfigVariables
from engine.file import FileManager
from engine.lib import Json
from engine.log import Log


CATEGORY_NAME = "WEB"

USER_DECK_FOLDER = ConfigVariables.Folder(
    'user_deck_folder',
    './deck/user-decks',
)
MARVELCDB_SYNC_STATE_FILE = ConfigVariables.File(
    'marvelcdb_sync_state_file',
    './deck/user-decks/.marvelcdb-sync-state.json',
)
MARVELCDB_SYNC_INTERVAL = ConfigVariables.Int(
    'marvelcdb_sync_interval',
    24 * 60 * 60,
)
STARTER_DECK_FOLDER = ConfigVariables.Folder(
    'starter_deck_folder',
    './deck/starter',
)
# Campaign decks live apart from './deck/user-decks' on purpose. The periodic
# sync rewrites `user-decks/{deck_id}.json` on a timer, so a campaign deck
# parked there could be silently replaced mid-run -- exactly the drift a frozen
# campaign deck exists to prevent.
CAMPAIGN_DECK_FOLDER = ConfigVariables.Folder(
    'campaign_deck_folder',
    './deck/campaign-decks',
)


class MarvelCdbDeckSync:

    API_URL = 'https://marvelcdb.com/api/public/deck/{deck_id}'
    DECKLIST_API_URL = 'https://marvelcdb.com/api/public/decklist/{deck_id}'
    STATE_VERSION = 1

    # MarvelCDB publishes two kinds of deck under separate endpoints:
    # `deck` is a user's own deck that they have shared, `decklist` is a
    # published decklist. Both are unauthenticated and return the same shape,
    # so the only thing that matters is picking the right one. A pasted link
    # tells us which; a bare ID does not, so we try both.
    DECK_KIND = 'deck'
    DECKLIST_KIND = 'decklist'
    DECK_KINDS = (DECK_KIND, DECKLIST_KIND)

    WEB_URL = 'https://marvelcdb.com/{kind}/view/{deck_id}'

    _URL_PATTERN = re.compile(
        r'marvelcdb\.com/(?:api/public/)?(deck|decklist)(?:/(?:view|edit))?/(\d+)',
        re.IGNORECASE,
    )

    # The exact shape CampaignDeckHeroId emits, and the only shape
    # CampaignDeckPath will interpolate into a filesystem path.
    _HERO_ID_PATTERN = re.compile(r'[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?')

    def __init__(
        self,
        *,
        user_deck_folder: str|None=None,
        state_file: str|None=None,
        starter_deck_folder: str|None=None,
        interval_seconds: int|None=None,
        fetch_deck: Callable[[str], Dict[str, Any]]|None=None,
        fetch_deck_ref: Callable[[str|None, str], Dict[str, Any]]|None=None,
        campaign_deck_folder: str|None=None,
    ) -> None:
        self.user_deck_folder = user_deck_folder or USER_DECK_FOLDER.value
        self.campaign_deck_folder = campaign_deck_folder or CAMPAIGN_DECK_FOLDER.value
        self.state_file = state_file or MARVELCDB_SYNC_STATE_FILE.value
        self.starter_deck_folder = starter_deck_folder or STARTER_DECK_FOLDER.value
        self.interval_seconds = (
            MARVELCDB_SYNC_INTERVAL.value
            if interval_seconds is None
            else interval_seconds
        )
        # Everything fetches through `fetch_deck_ref` now, because every caller
        # has a kind to pass -- `None` for a bare ID. The single-argument
        # `fetch_deck` is still accepted so existing callers and tests keep
        # working, and is adapted rather than kept as a second live seam: two
        # seams meant a test could stub one and leave the other reaching the
        # network.
        if fetch_deck_ref is not None:
            self.fetch_deck_ref = fetch_deck_ref
        elif fetch_deck is not None:
            self.fetch_deck_ref = lambda kind, deck_id: fetch_deck(deck_id)
        else:
            self.fetch_deck_ref = self.FetchDeckRef

        self._condition = threading.Condition(threading.RLock())
        self._sync_lock = threading.Lock()
        self._stopping = False
        self._thread: threading.Thread|None = None

    @classmethod
    def ParseDeckRef(cls, value: str) -> Tuple[str|None, str]:
        """Resolve a pasted MarvelCDB reference to a ``(kind, deck_id)`` pair.

        Accepts a bare numeric ID or any MarvelCDB deck/decklist URL. ``kind``
        is ``None`` for a bare ID: the number alone does not say which of the
        two endpoints holds it, so the caller has to try both.
        """
        reference = str(value).strip()
        if not reference:
            raise ValueError('Enter a MarvelCDB deck ID or link.')

        match = cls._URL_PATTERN.search(reference)
        if match:
            return match.group(1).lower(), str(int(match.group(2)))

        if reference.isascii() and reference.isdecimal():
            return None, str(int(reference))

        raise ValueError(f'Invalid MarvelCDB deck ID or link: {reference}')

    @classmethod
    def CanonicalRef(cls, kind: str|None, deck_id: str) -> str:
        """Render a ``(kind, deck_id)`` pair back to a single parseable string.

        A bare ID stays bare -- there is no kind to encode, and inventing one
        would make the two-endpoint fallback unreachable. This is the inverse of
        ParseDeckRef for every value ParseDeckRef can return, so a reference can
        round-trip through storage without losing which endpoint it named.
        """
        if kind not in cls.DECK_KINDS:
            return str(deck_id)
        return cls.WEB_URL.format(kind=kind, deck_id=deck_id)

    @classmethod
    def ParseDeckRefs(cls, value: str|List[str]) -> List[str]:
        """Normalise a comma-separated list of references for storage.

        Returns canonical references, NOT bare IDs. Returning bare IDs here
        discarded the kind that ParseDeckRef had just recovered, so a URL
        naming `decklist/123` was stored as `123` and the next periodic sync
        probed `deck/123` first -- fetching a different deck that happened to
        share the number. Bare IDs pass through unchanged, so existing sync
        state keeps working without a migration.
        """
        if not isinstance(value, (str, list)):
            raise ValueError('MarvelCDB deck IDs must be a comma-separated list.')
        values = value.split(',') if isinstance(value, str) else value
        refs: List[str] = []

        for raw_value in values:
            reference = str(raw_value).strip()
            if not reference:
                continue
            ref = cls.CanonicalRef(*cls.ParseDeckRef(reference))
            if ref not in refs:
                refs.append(ref)

        return refs

    @classmethod
    def _RequestJson(cls, url: str) -> Dict[str, Any]|None:
        """Fetch ``url``, returning the decoded object or ``None`` if it is not
        a JSON deck.

        MarvelCDB answers a miss with ``HTTP 200`` and an HTML page rather than
        a 404, so a non-JSON body is an ordinary "not on this endpoint" result
        and must stay distinguishable from a transport failure -- otherwise a
        bare ID could never fall through from one endpoint to the other, and a
        simple typo would surface as a raw JSONDecodeError.
        """
        request = Request(
            url,
            headers={
                'Accept': 'application/json',
                'User-Agent': 'Marvel Champions Digital: Ronin Edition/0.6.0',
            },
        )

        try:
            with urlopen(request, timeout=20) as response:
                payload = response.read().decode('utf-8')
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise ValueError(
                f'MarvelCDB returned HTTP {exc.code} for {url}.'
            ) from exc
        except URLError as exc:
            raise ValueError(
                f'Could not connect to MarvelCDB: {exc.reason}'
            ) from exc
        except UnicodeDecodeError:
            return None

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None

        return data if isinstance(data, dict) else None

    @classmethod
    def FetchDeckRef(cls, kind: str|None, deck_id: str) -> Dict[str, Any]:
        """Fetch a deck by ``kind``, or by trying both kinds when it is unknown."""
        for candidate in ((kind,) if kind else cls.DECK_KINDS):
            template = (
                cls.API_URL if candidate == cls.DECK_KIND else cls.DECKLIST_API_URL
            )
            data = cls._RequestJson(template.format(deck_id=deck_id))
            if data is not None:
                data.setdefault('marvelcdb_kind', candidate)
                return data

        if kind:
            raise ValueError(
                f'MarvelCDB {kind} {deck_id} was not found or is not shared publicly.'
            )
        raise ValueError(
            f'{deck_id} was not found as a MarvelCDB deck or decklist. '
            'Check the ID, or paste the full link.'
        )

    @classmethod
    def FetchDeck(cls, deck_id: str) -> Dict[str, Any]:
        return cls.FetchDeckRef(None, deck_id)

    @staticmethod
    def _card_faces(card: str) -> List[str]:
        return [face.strip().lower() for face in card.split(',') if face.strip()]

    @classmethod
    def _template_hero_codes(cls, template: Dict[str, Any]) -> set[str]:
        hero_codes: set[str] = set()
        for card in template.get('hero', []) + template.get('hero_deck', []):
            faces = cls._card_faces(card)
            hero_codes.update(faces)

            # MarvelCDB represents some double-sided cards without the face
            # suffix (for example, 26002 instead of 26002a/26002b).
            bases = {
                face[:-1] for face in faces
                if face.endswith(('a', 'b'))
            }
            if len(faces) > 1 and len(bases) == 1:
                hero_codes.update(bases)

        return hero_codes

    @classmethod
    def ConvertDeck(
        cls,
        remote_deck: Dict[str, Any],
        template: Dict[str, Any],
    ) -> Dict[str, Any]:
        deck_id = str(remote_deck.get('id', '')).strip()
        deck_name = str(remote_deck.get('name', '')).strip()
        slots = remote_deck.get('slots')

        if not deck_id.isdecimal():
            raise ValueError('MarvelCDB deck has no valid numeric ID.')
        if not deck_name:
            raise ValueError(f'MarvelCDB deck {deck_id} has no name.')
        if not isinstance(slots, dict):
            raise ValueError(f'MarvelCDB deck {deck_id} has no card slots.')

        hero_codes = cls._template_hero_codes(template)
        player_deck: List[str] = []
        for raw_card_id, raw_count in slots.items():
            card_id = str(raw_card_id).strip().lower()
            if not card_id:
                continue
            if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 0:
                raise ValueError(
                    f'MarvelCDB deck {deck_id} has an invalid count for {card_id}.'
                )
            if card_id in hero_codes:
                continue
            player_deck.extend([card_id] * raw_count)

        converted = copy.deepcopy(template)
        converted['deck_name'] = deck_name
        converted['player_deck'] = player_deck
        metadata = converted.setdefault('metadata', {})
        if not isinstance(metadata, dict):
            metadata = {}
            converted['metadata'] = metadata
        # Record which endpoint this came from. Without it a later refresh has
        # to guess, and guessing wrong silently fetches a different deck that
        # happens to share the ID.
        kind = str(remote_deck.get('marvelcdb_kind', '')).lower()
        if kind not in cls.DECK_KINDS:
            kind = cls.DECK_KIND
        metadata.update({
            'marvelcdb_id': deck_id,
            'marvelcdb_kind': kind,
            'marvelcdb_name': deck_name,
            'url': cls.WEB_URL.format(kind=kind, deck_id=deck_id),
            'date_update': str(remote_deck.get('date_update', '')),
        })
        return converted

    def _default_state(self) -> Dict[str, Any]:
        return {
            'version': self.STATE_VERSION,
            'deck_ids': [],
            'last_sync': '',
            'last_result': None,
        }

    @staticmethod
    def _read_json(file_path: str) -> Dict[str, Any]:
        with FileManager.OpenFile(file_path, read=True) as file:
            data = Json.Loads(file.Read())
        if not isinstance(data, dict):
            raise ValueError(f'{file_path} is not a JSON object')
        return data

    def _load_state(self) -> Dict[str, Any]:
        if not FileManager.Exists(self.state_file):
            return self._default_state()

        try:
            state = self._read_json(self.state_file)
            # The key keeps its historical name; it now holds canonical
            # references, and a bare ID is still a valid one.
            state['deck_ids'] = self.ParseDeckRefs(state.get('deck_ids', []))
            state.setdefault('version', self.STATE_VERSION)
            state.setdefault('last_sync', '')
            state.setdefault('last_result', None)
            return state
        except Exception as exc:
            Log.Warn(CATEGORY_NAME, f'Could not read MarvelCDB sync state: {exc}')
            return self._default_state()

    def _save_json(self, data: Dict[str, Any], file_path: str) -> None:
        FileManager.MakeDir(FileManager.GetDirName(file_path))
        temporary_path = f'{file_path}.tmp'
        with FileManager.OpenFile(temporary_path, write=True) as file:
            file.Write(Json.Dumps(data, indent=4))
        os.replace(temporary_path, file_path)

    def _save_state(self, state: Dict[str, Any]) -> None:
        self._save_json(state, self.state_file)

    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        templates: Dict[str, Dict[str, Any]] = {}
        for file_path in FileManager.ListFiles(self.starter_deck_folder, ext='.json'):
            template = self._read_json(file_path)
            for hero in template.get('hero', []):
                for hero_code in self._card_faces(hero):
                    templates[hero_code] = template
        return templates

    @staticmethod
    def _select_template(
        templates: Dict[str, Dict[str, Any]],
        remote_deck: Dict[str, Any],
    ) -> Dict[str, Any]:
        hero_code = str(remote_deck.get('hero_code', '')).lower()
        template = templates.get(hero_code)
        if template is None:
            hero_name = str(remote_deck.get('hero_name', 'Unknown hero'))
            raise ValueError(
                f'{hero_name} ({hero_code or "no hero code"}) has no '
                'starter deck in this installation.'
            )
        return template

    @classmethod
    def _deck_hero_code(cls, deck: Dict[str, Any]) -> str:
        for hero in deck.get('hero', []):
            faces = cls._card_faces(hero)
            if faces:
                return faces[0]
        return ''

    @staticmethod
    def _count_card_changes(before: List[str], after: List[str]) -> int:
        counted_before = Counter(before)
        counted_after = Counter(after)
        difference = (counted_before - counted_after) + (counted_after - counted_before)
        return sum(difference.values())

    def ResolveDeck(self, reference: str) -> Dict[str, Any]:
        """Fetch and convert a MarvelCDB deck without writing anything to disk.

        Quick Play uses this: the converted deck goes straight to `/new` as
        `hero_json`, so trying a netdeck never leaves a file behind to clean up.
        """
        kind, deck_id = self.ParseDeckRef(reference)
        remote_deck = self.fetch_deck_ref(kind, deck_id)
        template = self._select_template(self._load_templates(), remote_deck)
        return self.ConvertDeck(remote_deck, template)

    @classmethod
    def ValidateCampaignHeroId(cls, hero_id: str) -> str:
        """Accept only the shape CampaignDeckHeroId produces.

        `hero_id` arrives from an HTTP body, and CampaignDeckPath puts it in a
        filesystem path, so anything outside this alphabet is a traversal
        attempt: `../../outside` would otherwise resolve above the campaign
        folder and let a refresh read and overwrite an unrelated file. The
        alphabet excludes `.`, `/` and `\\` entirely, which is what makes
        traversal unrepresentable rather than merely detected.
        """
        candidate = str(hero_id).strip()
        if not cls._HERO_ID_PATTERN.fullmatch(candidate):
            raise ValueError(f'Invalid campaign deck name: {hero_id!r}')
        return candidate

    def CampaignDeckPath(self, hero_id: str) -> str:
        safe_id = self.ValidateCampaignHeroId(hero_id)
        folder = os.path.realpath(self.campaign_deck_folder)
        path = os.path.realpath(FileManager.JoinPath(folder, f'{safe_id}.json'))

        # Belt and braces: unreachable while the alphabet holds, so if it fires
        # the alphabet has regressed. The order matters -- containment cannot be
        # the primary guard, because `sub/outside`, `..` and `name.with.dots`
        # all resolve to paths that are legitimately inside this folder and
        # would pass it while still not being names we ever generate.
        if os.path.commonpath([folder, path]) != folder:
            raise ValueError(f'Invalid campaign deck name: {hero_id!r}')
        return path

    @classmethod
    def CampaignDeckHeroId(cls, campaign_id: str, hero_code: str) -> str:
        campaign = str(campaign_id).strip()
        hero = str(hero_code).strip()
        if not campaign or not hero:
            raise ValueError('A campaign deck needs both a campaign and a hero.')

        combined = f'{campaign}-{hero}'.lower()
        hero_id = re.sub(r'[^a-z0-9_-]+', '-', combined).strip('-_')
        # Both parts were non-empty but may have held nothing usable, and the
        # result has to satisfy the validator that guards the path.
        return cls.ValidateCampaignHeroId(hero_id)

    def SaveCampaignDeck(self, campaign_id: str, deck: Dict[str, Any]) -> Dict[str, Any]:
        """Freeze a resolved deck for the duration of a campaign run.

        Campaigns persist their hero as a deck-file id, so a netdeck has to
        become a real file for `heroId` to keep working. Frozen is the point:
        it only changes when the player asks it to, via RefreshCampaignDeck.
        """
        hero_id = self.CampaignDeckHeroId(campaign_id, self._deck_hero_code(deck))
        self._save_json(deck, self.CampaignDeckPath(hero_id))
        return {'hero_id': hero_id, 'deck': deck}

    def RefreshCampaignDeck(self, hero_id: str) -> Dict[str, Any]:
        """Re-pull a frozen campaign deck from MarvelCDB, on explicit request."""
        deck_path = self.CampaignDeckPath(hero_id)
        if not FileManager.Exists(deck_path):
            raise ValueError('No campaign deck was saved under that name.')

        current = self._read_json(deck_path)
        metadata = current.get('metadata') or {}
        deck_id = str(metadata.get('marvelcdb_id', '')).strip()
        if not deck_id:
            raise ValueError('That campaign deck did not come from MarvelCDB.')
        kind = str(metadata.get('marvelcdb_kind', '')).lower() or None

        remote_deck = self.fetch_deck_ref(kind, deck_id)
        template = self._select_template(self._load_templates(), remote_deck)
        updated = self.ConvertDeck(remote_deck, template)

        # Rebuilding between scenarios is legal; swapping hero is not.
        if self._deck_hero_code(updated) != self._deck_hero_code(current):
            raise ValueError(
                'That MarvelCDB deck now plays a different hero, and a campaign '
                'cannot change hero mid-run.'
            )

        changed = self._count_card_changes(
            current.get('player_deck', []),
            updated.get('player_deck', []),
        )
        self._save_json(updated, deck_path)
        return {'hero_id': hero_id, 'deck': updated, 'changed': changed}

    def GetStatus(self) -> Dict[str, Any]:
        with self._condition:
            state = self._load_state()
            return copy.deepcopy(state)

    def SyncDecks(self, deck_ids_value: str|List[str]) -> Dict[str, Any]:
        deck_refs = self.ParseDeckRefs(deck_ids_value)
        if not deck_refs:
            raise ValueError('Enter at least one MarvelCDB deck ID.')

        with self._sync_lock:
            with self._condition:
                state = self._load_state()
                state['deck_ids'] = deck_refs
                self._save_state(state)
                self._condition.notify_all()

            templates = self._load_templates()
            synced: List[Dict[str, str]] = []
            errors: List[Dict[str, str]] = []

            for deck_ref in deck_refs:
                kind, deck_id = self.ParseDeckRef(deck_ref)
                try:
                    remote_deck = self.fetch_deck_ref(kind, deck_id)
                    returned_id = str(remote_deck.get('id', ''))
                    if returned_id != deck_id:
                        raise ValueError(
                            f'MarvelCDB returned deck {returned_id or "without an ID"} '
                            f'instead of {deck_id}.'
                        )

                    template = self._select_template(templates, remote_deck)
                    converted = self.ConvertDeck(remote_deck, template)
                    output_path = FileManager.JoinPath(
                        self.user_deck_folder,
                        f'{deck_id}.json',
                    )
                    self._save_json(converted, output_path)
                    synced.append({
                        'id': deck_id,
                        'name': converted['deck_name'],
                        'hero': converted['name'],
                        'file': output_path,
                    })
                except Exception as exc:
                    errors.append({'id': deck_id, 'error': str(exc)})

            result: Dict[str, Any] = {
                'ok': not errors,
                'synced': synced,
                'errors': errors,
                'synced_at': datetime.now(timezone.utc).isoformat(),
            }
            with self._condition:
                state = self._load_state()
                state['deck_ids'] = deck_refs
                state['last_sync'] = result['synced_at']
                state['last_result'] = result
                self._save_state(state)
                self._condition.notify_all()

        if synced:
            Log.Info(
                CATEGORY_NAME,
                f'MarvelCDB: synced {len(synced)} user deck(s).',
            )
        for error in errors:
            Log.Warn(
                CATEGORY_NAME,
                f'MarvelCDB deck {error["id"]}: {error["error"]}',
            )
        return result

    def _seconds_until_sync(self, state: Dict[str, Any]) -> float|None:
        if not state.get('deck_ids'):
            return None

        last_sync = str(state.get('last_sync', '')).strip()
        if not last_sync:
            return 0
        try:
            synced_at = datetime.fromisoformat(last_sync)
            if synced_at.tzinfo is None:
                synced_at = synced_at.replace(tzinfo=timezone.utc)
        except ValueError:
            return 0

        next_sync = synced_at + timedelta(seconds=self.interval_seconds)
        return max(0, (next_sync - datetime.now(timezone.utc)).total_seconds())

    def _run_periodic_sync(self) -> None:
        while True:
            with self._condition:
                if self._stopping:
                    return
                state = self._load_state()
                wait_seconds = self._seconds_until_sync(state)
                if wait_seconds is None or wait_seconds > 0:
                    self._condition.wait(timeout=wait_seconds)
                    continue
                deck_ids = state['deck_ids']

            try:
                self.SyncDecks(deck_ids)
            except Exception as exc:
                Log.Warn(CATEGORY_NAME, f'MarvelCDB periodic sync failed: {exc}')

    def Start(self) -> None:
        with self._condition:
            if self._thread and self._thread.is_alive():
                return
            self._stopping = False
            self._thread = threading.Thread(
                target=self._run_periodic_sync,
                name='MarvelCDB Sync',
                daemon=True,
            )
            self._thread.start()

    def Stop(self) -> None:
        with self._condition:
            self._stopping = True
            self._condition.notify_all()
        if self._thread:
            self._thread.join(timeout=25)
