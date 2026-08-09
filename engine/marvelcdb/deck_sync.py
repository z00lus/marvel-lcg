from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
import os
import threading
from typing import Any, Callable, Dict, List
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


class MarvelCdbDeckSync:

    API_URL = 'https://marvelcdb.com/api/public/deck/{deck_id}'
    STATE_VERSION = 1

    def __init__(
        self,
        *,
        user_deck_folder: str|None=None,
        state_file: str|None=None,
        starter_deck_folder: str|None=None,
        interval_seconds: int|None=None,
        fetch_deck: Callable[[str], Dict[str, Any]]|None=None,
    ) -> None:
        self.user_deck_folder = user_deck_folder or USER_DECK_FOLDER.value
        self.state_file = state_file or MARVELCDB_SYNC_STATE_FILE.value
        self.starter_deck_folder = starter_deck_folder or STARTER_DECK_FOLDER.value
        self.interval_seconds = (
            MARVELCDB_SYNC_INTERVAL.value
            if interval_seconds is None
            else interval_seconds
        )
        self.fetch_deck = fetch_deck or self.FetchDeck

        self._condition = threading.Condition(threading.RLock())
        self._sync_lock = threading.Lock()
        self._stopping = False
        self._thread: threading.Thread|None = None

    @staticmethod
    def ParseDeckIds(value: str|List[str]) -> List[str]:
        if not isinstance(value, (str, list)):
            raise ValueError('MarvelCDB deck IDs must be a comma-separated list.')
        values = value.split(',') if isinstance(value, str) else value
        deck_ids: List[str] = []

        for raw_value in values:
            deck_id = str(raw_value).strip()
            if not deck_id:
                continue
            if not deck_id.isascii() or not deck_id.isdecimal():
                raise ValueError(f'Invalid MarvelCDB deck ID: {deck_id}')
            normalized = str(int(deck_id))
            if normalized not in deck_ids:
                deck_ids.append(normalized)

        return deck_ids

    @staticmethod
    def FetchDeck(deck_id: str) -> Dict[str, Any]:
        request = Request(
            MarvelCdbDeckSync.API_URL.format(deck_id=deck_id),
            headers={
                'Accept': 'application/json',
                'User-Agent': 'Marvel Champions Digital: Ronin Edition/0.6.0',
            },
        )

        try:
            with urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode('utf-8'))
        except HTTPError as exc:
            if exc.code == 404:
                raise ValueError(
                    f'Deck {deck_id} was not found or is not shared publicly.'
                ) from exc
            raise ValueError(
                f'MarvelCDB returned HTTP {exc.code} for deck {deck_id}.'
            ) from exc
        except URLError as exc:
            raise ValueError(
                f'Could not connect to MarvelCDB for deck {deck_id}: {exc.reason}'
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                f'MarvelCDB returned invalid JSON for deck {deck_id}.'
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(f'MarvelCDB returned invalid data for deck {deck_id}.')
        return data

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
        metadata.update({
            'marvelcdb_id': deck_id,
            'marvelcdb_name': deck_name,
            'url': f'https://marvelcdb.com/deck/view/{deck_id}',
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
            state['deck_ids'] = self.ParseDeckIds(state.get('deck_ids', []))
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

    def GetStatus(self) -> Dict[str, Any]:
        with self._condition:
            state = self._load_state()
            return copy.deepcopy(state)

    def SyncDecks(self, deck_ids_value: str|List[str]) -> Dict[str, Any]:
        deck_ids = self.ParseDeckIds(deck_ids_value)
        if not deck_ids:
            raise ValueError('Enter at least one MarvelCDB deck ID.')

        with self._sync_lock:
            with self._condition:
                state = self._load_state()
                state['deck_ids'] = deck_ids
                self._save_state(state)
                self._condition.notify_all()

            templates = self._load_templates()
            synced: List[Dict[str, str]] = []
            errors: List[Dict[str, str]] = []

            for deck_id in deck_ids:
                try:
                    remote_deck = self.fetch_deck(deck_id)
                    returned_id = str(remote_deck.get('id', ''))
                    if returned_id != deck_id:
                        raise ValueError(
                            f'MarvelCDB returned deck {returned_id or "without an ID"} '
                            f'instead of {deck_id}.'
                        )

                    hero_code = str(remote_deck.get('hero_code', '')).lower()
                    template = templates.get(hero_code)
                    if template is None:
                        hero_name = str(remote_deck.get('hero_name', 'Unknown hero'))
                        raise ValueError(
                            f'{hero_name} ({hero_code or "no hero code"}) has no '
                            'starter deck in this installation.'
                        )

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
                state['deck_ids'] = deck_ids
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
