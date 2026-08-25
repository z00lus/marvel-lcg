from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sqlite3
import threading
from typing import Any, Dict, List, TYPE_CHECKING
import uuid

from core.lib import Time
from engine.config import ConfigVariables
from engine.file import FileManager
from engine.log import Log
from game.statistics.achievements import AchievementEvaluator

if TYPE_CHECKING:
    from game.statistics.replay_outcome_analyzer import ReplayOutcomeAnalyzer


CATEGORY_NAME = 'STATISTICS'

GAME_HISTORY = ConfigVariables.Bool('game_history', True)
GAME_HISTORY_FILE = ConfigVariables.File(
    'game_history_file',
    './statistics.sqlite3',
)
REPLAY_FOLDERS = ConfigVariables.Folders('replay_folders', ['./replays/'])


class GameHistory:
    SCHEMA_VERSION = 4
    KNOWN_RESULTS = ('win', 'loss', 'unknown', 'abandoned')
    KNOWN_SOURCES = ('digital', 'physical', 'replay_import')

    def __init__(self, file_path: str|None=None, replay_folders: List[str]|None=None) -> None:
        self.file_path = file_path or GAME_HISTORY_FILE.value
        self.replay_folders = replay_folders if replay_folders is not None else REPLAY_FOLDERS.value
        self.enabled = GAME_HISTORY.value
        self.available = False
        self._lock = threading.RLock()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.file_path, timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('PRAGMA busy_timeout = 20000')
        return connection

    def Initialize(
        self,
        outcome_analyzer: 'ReplayOutcomeAnalyzer|None'=None,
    ) -> None:
        if not self.enabled:
            return
        try:
            database_existed = FileManager.IsFile(self.file_path)
            FileManager.MakeDir(FileManager.GetDirName(self.file_path))
            with self._lock, self._connect() as connection:
                connection.execute('PRAGMA journal_mode = WAL')
                connection.execute('PRAGMA synchronous = NORMAL')
                self._migrate(connection)
            self.available = True
            imported = (
                0
                if database_existed
                else self.ImportReplays(outcome_analyzer)
            )
            Log.Info(
                CATEGORY_NAME,
                f'Game history ready: {self.file_path} ({imported} replay(s) imported)',
            )
        except Exception as exc:
            self.available = False
            Log.FailedTrace(CATEGORY_NAME, exc, no_take_as_error=True)

    def Close(self) -> None:
        # Connections are deliberately short-lived and closed per operation.
        pass

    def _migrate(self, connection: sqlite3.Connection) -> None:
        version = int(connection.execute('PRAGMA user_version').fetchone()[0])
        if version > self.SCHEMA_VERSION:
            raise RuntimeError(
                f'Game history schema {version} is newer than supported '
                f'{self.SCHEMA_VERSION}.'
            )
        if version == 0:
            connection.executescript(
                '''
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_key TEXT NOT NULL UNIQUE,
                    finished_at TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    engine_version TEXT NOT NULL DEFAULT '',
                    rules_version TEXT NOT NULL DEFAULT '',
                    hero_code TEXT NOT NULL DEFAULT '',
                    hero_name TEXT NOT NULL DEFAULT '',
                    villain_code TEXT NOT NULL DEFAULT '',
                    villain_name TEXT NOT NULL DEFAULT '',
                    scenario_name TEXT NOT NULL DEFAULT '',
                    scenario_key TEXT NOT NULL DEFAULT '',
                    expert INTEGER NOT NULL DEFAULT 0 CHECK (expert IN (0, 1)),
                    result TEXT NOT NULL DEFAULT 'unknown'
                        CHECK (result IN ('win', 'loss', 'unknown', 'abandoned')),
                    game_over_reason TEXT NOT NULL DEFAULT '',
                    rounds INTEGER,
                    playtime_seconds REAL,
                    seed INTEGER,
                    campaign_id TEXT NOT NULL DEFAULT '',
                    game_mode TEXT NOT NULL DEFAULT 'quick',
                    deck_name TEXT NOT NULL DEFAULT '',
                    deck_source TEXT NOT NULL DEFAULT '',
                    remaining_hit_points INTEGER,
                    minions_in_play INTEGER,
                    side_schemes_in_play INTEGER,
                    undo_count INTEGER,
                    replay_file TEXT NOT NULL DEFAULT '',
                    imported_from_replay INTEGER NOT NULL DEFAULT 0
                        CHECK (imported_from_replay IN (0, 1)),
                    replay_analysis_status TEXT NOT NULL DEFAULT '',
                    replay_analysis_error TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'digital'
                        CHECK (source IN ('digital', 'physical', 'replay_import')),
                    notes TEXT NOT NULL DEFAULT '',
                    hero_rating INTEGER CHECK (hero_rating BETWEEN 1 AND 5),
                    scenario_rating INTEGER CHECK (scenario_rating BETWEEN 1 AND 5)
                );

                CREATE INDEX IF NOT EXISTS games_result_index
                    ON games(result, id);
                CREATE INDEX IF NOT EXISTS games_hero_index
                    ON games(hero_code, result);
                CREATE INDEX IF NOT EXISTS games_scenario_index
                    ON games(scenario_key, result);
                CREATE INDEX IF NOT EXISTS games_matchup_index
                    ON games(hero_code, scenario_key, expert, result);
                CREATE INDEX IF NOT EXISTS games_source_index
                    ON games(source, result, id);

                CREATE TABLE IF NOT EXISTS game_card_statistics (
                    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                    card_id TEXT NOT NULL,
                    card_name TEXT NOT NULL DEFAULT '',
                    damage_dealt INTEGER NOT NULL DEFAULT 0,
                    damage_taken INTEGER NOT NULL DEFAULT 0,
                    thwarted_threat INTEGER NOT NULL DEFAULT 0,
                    entered_play INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (game_id, card_id)
                );

                CREATE TABLE IF NOT EXISTS achievements (
                    achievement_id TEXT PRIMARY KEY,
                    unlocked_at TEXT NOT NULL,
                    unlocked_game_id INTEGER REFERENCES games(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS collection_products (
                    product_key TEXT PRIMARY KEY,
                    owned_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                '''
            )
            connection.execute(f'PRAGMA user_version = {self.SCHEMA_VERSION}')
            version = self.SCHEMA_VERSION

        if version < 2:
            connection.execute(
                "ALTER TABLE games ADD COLUMN replay_analysis_status "
                "TEXT NOT NULL DEFAULT ''"
            )
            connection.execute(
                "ALTER TABLE games ADD COLUMN replay_analysis_error "
                "TEXT NOT NULL DEFAULT ''"
            )
            connection.execute('PRAGMA user_version = 2')
            version = 2

        if version < 3:
            columns = {
                row['name'] for row in connection.execute(
                    'PRAGMA table_info(games)'
                ).fetchall()
            }
            if 'source' not in columns:
                connection.execute(
                    "ALTER TABLE games ADD COLUMN source TEXT NOT NULL "
                    "DEFAULT 'digital' CHECK (source IN "
                    "('digital', 'physical', 'replay_import'))"
                )
            if 'notes' not in columns:
                connection.execute(
                    "ALTER TABLE games ADD COLUMN notes TEXT NOT NULL DEFAULT ''"
                )
            if 'imported_from_replay' in columns:
                connection.execute(
                    "UPDATE games SET source = 'replay_import' "
                    'WHERE imported_from_replay = 1'
                )
            connection.executescript(
                '''
                CREATE INDEX IF NOT EXISTS games_source_index
                    ON games(source, result, id);
                CREATE TABLE IF NOT EXISTS collection_products (
                    product_key TEXT PRIMARY KEY,
                    owned_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                '''
            )
            connection.execute('PRAGMA user_version = 3')
            version = 3

        if version < 4:
            columns = {
                row['name'] for row in connection.execute(
                    'PRAGMA table_info(games)'
                ).fetchall()
            }
            if 'hero_rating' not in columns:
                connection.execute(
                    'ALTER TABLE games ADD COLUMN hero_rating INTEGER '
                    'CHECK (hero_rating BETWEEN 1 AND 5)'
                )
            if 'scenario_rating' not in columns:
                connection.execute(
                    'ALTER TABLE games ADD COLUMN scenario_rating INTEGER '
                    'CHECK (scenario_rating BETWEEN 1 AND 5)'
                )
            connection.execute('PRAGMA user_version = 4')

    @staticmethod
    def NewGameId() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _slug(value: str) -> str:
        value = value.strip().lower().replace('&', ' and ')
        return re.sub(r'[^a-z0-9]+', '_', value).strip('_')

    @staticmethod
    def _first_card_id(cards: Any) -> str:
        if not isinstance(cards, list) or not cards:
            return ''
        return str(cards[0]).split(',')[0].strip().lower()

    @staticmethod
    def _safe_int(value: Any) -> int|None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_float(value: Any) -> float|None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _normalize_finished_at(cls, value: Any, file_path: str) -> str:
        text = str(value or '').strip()
        if text:
            try:
                return datetime.fromisoformat(text).isoformat()
            except ValueError:
                try:
                    local_time = datetime.strptime(text, '%Y-%m-%d %H-%M')
                    return local_time.astimezone().isoformat()
                except ValueError:
                    pass
        return datetime.fromtimestamp(
            os.path.getmtime(file_path),
            timezone.utc,
        ).isoformat()

    @classmethod
    def EnsureSceneGameId(cls, scene: Any) -> str:
        game_id = scene.GetMetadataStr('game_id')
        if not game_id:
            game_id = cls.NewGameId()
            scene.SetMetadataStr('game_id', game_id)
        return game_id

    @staticmethod
    def ResetSceneOutcome(scene: Any) -> None:
        for key in (
            'game_id',
            'game_result',
            'game_over_reason',
            'statistics_eligible',
            'rounds',
            'remaining_hit_points',
            'minions_in_play',
            'side_schemes_in_play',
            'undo_count',
            'time',
            'playtime',
            'path',
        ):
            scene.metadata.pop(key, None)

    @staticmethod
    def CaptureOutcomeMetadata(game: Any, players_won: bool, reason: str) -> None:
        scene = game.scene
        world = game.world
        if not world:
            return
        scene.SetMetadataStr('game_result', 'win' if players_won else 'loss')
        scene.SetMetadataStr('game_over_reason', reason)
        scene.SetMetadataBool(
            'statistics_eligible',
            GameHistory.IsEligibleLiveGame(game),
        )
        scene.SetMetadataInt('rounds', world.round_id)
        scene.SetMetadataInt('undo_count', game.session.undo_count)
        if len(world.const_players) == 1:
            player = world.const_players[0]
            scene.SetMetadataInt(
                'remaining_hit_points',
                max(0, int(player.GetIdentity().health)),
            )
            scene.SetMetadataInt('minions_in_play', len(player.GetEngagedMinions()))
            scene.SetMetadataInt(
                'side_schemes_in_play',
                world.area_schemes_side.GetSize(),
            )

    @staticmethod
    def IsEligibleLiveGame(game: Any) -> bool:
        if not game.world or not game.session.scene:
            return False
        if len(game.world.const_players) != 1:
            return False
        if game.scene.is_puzzle or game.controller_manager.replay.is_replay:
            return False
        if game.session.cheat:
            return False
        if any(
            getattr(item, 'effect', None) and item.effect.GetDebugCommand()
            for item in game.controller_manager.replay.history_inputs
        ):
            return False
        from game.test import Test
        return not Test.IsInTesting()

    def _should_record_live_game(self, game: Any) -> bool:
        return self.available and self.IsEligibleLiveGame(game)

    def _live_record(self, game: Any) -> Dict[str, Any]:
        scene = game.scene
        world = game.world
        assert world
        player = scene.players[0]
        campaign = scene.campaign
        result = 'win' if world.game_over.players_won else 'loss'
        game_id = self.EnsureSceneGameId(scene)
        villain_code = self._first_card_id(campaign.villain or campaign.schemes)
        scenario_name = campaign.name or villain_code
        metadata = getattr(player, 'metadata', {}) or {}
        playtime = max(0.0, Time.GetTime() - game.session.start_time + scene.playtime)
        return {
            'source_key': f'game:{game_id}',
            'finished_at': self._now(),
            'engine_version': scene.version,
            'rules_version': 'v18' if 'v18_all' in scene.rules else '',
            'hero_code': self._first_card_id(player.hero),
            'hero_name': player.name,
            'villain_code': villain_code,
            'villain_name': scenario_name,
            'scenario_name': scenario_name,
            'scenario_key': self._slug(scenario_name),
            'expert': int(bool(campaign.expert)),
            'result': result,
            'game_over_reason': str(world.game_over.reason or ''),
            'rounds': world.round_id,
            'playtime_seconds': playtime,
            'seed': scene.seed,
            'campaign_id': campaign.campaign_id,
            'game_mode': 'campaign' if 'mode_campaign' in scene.rules else 'quick',
            'deck_name': getattr(player, 'deck_name', '') or player.name,
            'deck_source': str(metadata.get('source', metadata.get('url', 'starter'))),
            'remaining_hit_points': scene.GetMetadataInt('remaining_hit_points'),
            'minions_in_play': scene.GetMetadataInt('minions_in_play'),
            'side_schemes_in_play': scene.GetMetadataInt('side_schemes_in_play'),
            'undo_count': game.session.undo_count,
            'replay_file': scene.path,
            'imported_from_replay': 0,
            'source': 'digital',
        }

    def _live_card_statistics(self, game: Any) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        world = game.world
        if not world:
            return []
        for object_id, values in game.session.statistics.dic.items():
            card = world.object_manager.card_dict.get(object_id)
            if not card:
                continue
            card_id = card.face.paper.card_id
            row = grouped.setdefault(card_id, {
                'card_id': card_id,
                'card_name': card.face.name,
                'damage_dealt': 0,
                'damage_taken': 0,
                'thwarted_threat': 0,
                'entered_play': 0,
            })
            for key in ('damage_dealt', 'damage_taken', 'thwarted_threat', 'entered_play'):
                row[key] += int(values.get(key, 0))
        return list(grouped.values())

    def RecordCompletedGame(self, game: Any) -> List[str]:
        if not self._should_record_live_game(game):
            return []
        record = self._live_record(game)
        return self._store_game(record, self._live_card_statistics(game))['unlocked']

    def _store_game(
        self,
        record: Dict[str, Any],
        card_statistics: List[Dict[str, Any]]|None=None,
    ) -> Dict[str, Any]:
        if not self.available:
            return {
                'inserted': False,
                'updated': False,
                'id': None,
                'unlocked': [],
            }
        columns = (
            'source_key', 'finished_at', 'imported_at', 'engine_version',
            'rules_version', 'hero_code', 'hero_name', 'villain_code',
            'villain_name', 'scenario_name', 'scenario_key', 'expert', 'result',
            'game_over_reason', 'rounds', 'playtime_seconds', 'seed',
            'campaign_id', 'game_mode', 'deck_name', 'deck_source',
            'remaining_hit_points', 'minions_in_play', 'side_schemes_in_play',
            'undo_count', 'replay_file', 'imported_from_replay',
            'replay_analysis_status', 'replay_analysis_error',
            'source', 'notes', 'hero_rating', 'scenario_rating',
        )
        values = {
            'source_key': '',
            'finished_at': self._now(),
            'imported_at': self._now(),
            'engine_version': '',
            'rules_version': '',
            'hero_code': '',
            'hero_name': '',
            'villain_code': '',
            'villain_name': '',
            'scenario_name': '',
            'scenario_key': '',
            'expert': 0,
            'result': 'unknown',
            'game_over_reason': '',
            'rounds': None,
            'playtime_seconds': None,
            'seed': None,
            'campaign_id': '',
            'game_mode': 'quick',
            'deck_name': '',
            'deck_source': '',
            'remaining_hit_points': None,
            'minions_in_play': None,
            'side_schemes_in_play': None,
            'undo_count': None,
            'replay_file': '',
            'imported_from_replay': 0,
            'replay_analysis_status': '',
            'replay_analysis_error': '',
            'source': 'digital',
            'notes': '',
            'hero_rating': None,
            'scenario_rating': None,
            **record,
        }
        if not values['source_key']:
            raise ValueError('A game history source key is required.')
        if values['result'] not in self.KNOWN_RESULTS:
            values['result'] = 'unknown'
        if values['source'] not in self.KNOWN_SOURCES:
            raise ValueError('Unknown game source.')

        placeholders = ','.join('?' for _ in columns)
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                f'INSERT OR IGNORE INTO games ({",".join(columns)}) '
                f'VALUES ({placeholders})',
                tuple(values[column] for column in columns),
            )
            inserted = bool(cursor.rowcount)
            row = connection.execute(
                'SELECT id, result FROM games WHERE source_key = ?',
                (values['source_key'],),
            ).fetchone()
            assert row is not None
            database_game_id = int(row['id'])

            outcome_updated = False
            if not inserted and values.get('replay_file'):
                connection.execute(
                    'UPDATE games SET replay_file = ?, '
                    'playtime_seconds = COALESCE(?, playtime_seconds), '
                    'replay_analysis_status = ?, replay_analysis_error = ? '
                    'WHERE id = ?',
                    (
                        values['replay_file'],
                        values.get('playtime_seconds'),
                        values.get('replay_analysis_status', ''),
                        values.get('replay_analysis_error', ''),
                        database_game_id,
                    ),
                )

                if row['result'] == 'unknown' and values['result'] in ('win', 'loss'):
                    connection.execute(
                        'UPDATE games SET result = ?, game_over_reason = ?, '
                        'rounds = COALESCE(?, rounds), '
                        'remaining_hit_points = COALESCE(?, remaining_hit_points), '
                        'minions_in_play = COALESCE(?, minions_in_play), '
                        'side_schemes_in_play = COALESCE(?, side_schemes_in_play) '
                        'WHERE id = ?',
                        (
                            values['result'],
                            values.get('game_over_reason', ''),
                            values.get('rounds'),
                            values.get('remaining_hit_points'),
                            values.get('minions_in_play'),
                            values.get('side_schemes_in_play'),
                            database_game_id,
                        ),
                    )
                    outcome_updated = True

            if inserted and card_statistics:
                connection.executemany(
                    'INSERT INTO game_card_statistics '
                    '(game_id, card_id, card_name, damage_dealt, damage_taken, '
                    'thwarted_threat, entered_play) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    [(
                        database_game_id,
                        item['card_id'],
                        item['card_name'],
                        item['damage_dealt'],
                        item['damage_taken'],
                        item['thwarted_threat'],
                        item['entered_play'],
                    ) for item in card_statistics],
                )

            unlocked = AchievementEvaluator.UnlockEarned(
                connection,
                database_game_id,
                str(values['finished_at']),
            ) if (inserted or outcome_updated) and values['result'] in ('win', 'loss') else []
            return {
                'inserted': inserted,
                'updated': outcome_updated,
                'id': database_game_id,
                'unlocked': unlocked,
            }

    @staticmethod
    def _file_hash(file_path: str) -> str:
        digest = hashlib.sha256()
        with open(file_path, 'rb') as file:
            for block in iter(lambda: file.read(1024 * 1024), b''):
                digest.update(block)
        return digest.hexdigest()

    def _record_from_replay(self, file_path: str) -> Dict[str, Any]:
        if os.path.getsize(file_path) > 100 * 1024 * 1024:
            raise ValueError('Replay is too large to import.')
        with open(file_path, encoding='utf-8') as file:
            raw = json.load(file)
        if not isinstance(raw, dict):
            raise ValueError('Replay root is not a JSON object.')

        metadata = raw.get('metadata') if isinstance(raw.get('metadata'), dict) else {}
        campaign = raw.get('campaign') if isinstance(raw.get('campaign'), dict) else {}
        players = raw.get('players') if isinstance(raw.get('players'), list) else []
        if len(players) != 1:
            raise ValueError('Only solo replays are imported into game history.')
        if raw.get('puzzle') or metadata.get('is_puzzle'):
            raise ValueError('Puzzle replays are not game history.')
        if metadata.get('statistics_eligible') is False:
            raise ValueError('Replay is marked as ineligible for statistics.')
        if '-debug' in os.path.basename(file_path).lower():
            raise ValueError('Debug replays are not game history.')
        player = players[0] if players and isinstance(players[0], dict) else {}
        rules = raw.get('rules') if isinstance(raw.get('rules'), list) else []
        replay_game_id = str(metadata.get('game_id', '')).strip()
        source_key = (
            f'game:{replay_game_id}'
            if replay_game_id
            else f'replay:{self._file_hash(file_path)}'
        )
        result = str(metadata.get('game_result', 'unknown')).lower()
        if result not in ('win', 'loss'):
            result = 'unknown'
        villain_code = self._first_card_id(
            campaign.get('villain') or campaign.get('schemes')
        )
        scenario_name = str(campaign.get('name', '') or villain_code)
        player_metadata = player.get('metadata') if isinstance(player.get('metadata'), dict) else {}
        saved_time = self._normalize_finished_at(metadata.get('time'), file_path)
        return {
            'source_key': source_key,
            'finished_at': saved_time,
            'engine_version': str(raw.get('version', '')),
            'rules_version': 'v18' if 'v18_all' in rules else 'legacy',
            'hero_code': self._first_card_id(player.get('hero')),
            'hero_name': str(player.get('name', '')),
            'villain_code': villain_code,
            'villain_name': scenario_name,
            'scenario_name': scenario_name,
            'scenario_key': self._slug(scenario_name),
            'expert': int(bool(campaign.get('expert', False))),
            'result': result,
            'game_over_reason': str(metadata.get('game_over_reason', '')),
            'rounds': self._safe_int(metadata.get('rounds')),
            'playtime_seconds': self._safe_float(metadata.get('playtime')),
            'seed': self._safe_int(metadata.get('seed')),
            'campaign_id': str(campaign.get('campaign_id', '')),
            'game_mode': 'campaign' if 'mode_campaign' in rules else 'quick',
            'deck_name': str(player.get('deck_name', '') or player.get('name', '')),
            'deck_source': str(player_metadata.get('source', player_metadata.get('url', 'replay'))),
            'remaining_hit_points': self._safe_int(metadata.get('remaining_hit_points')),
            'minions_in_play': self._safe_int(metadata.get('minions_in_play')),
            'side_schemes_in_play': self._safe_int(metadata.get('side_schemes_in_play')),
            'undo_count': self._safe_int(metadata.get('undo_count')),
            'replay_file': os.path.abspath(file_path),
            'imported_from_replay': 1,
            'replay_analysis_status': 'metadata' if result in ('win', 'loss') else 'pending',
            'replay_analysis_error': '',
            'source': 'replay_import',
            'notes': '',
        }

    def _existing_replay_state(self, source_key: str) -> Dict[str, str]:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                'SELECT result, replay_analysis_status, replay_analysis_error '
                'FROM games WHERE source_key = ?',
                (source_key,),
            ).fetchone()
            return {
                'result': str(row['result']),
                'status': str(row['replay_analysis_status']),
                'error': str(row['replay_analysis_error']),
            } if row else {'result': '', 'status': '', 'error': ''}

    def ImportReplays(
        self,
        outcome_analyzer: 'ReplayOutcomeAnalyzer|None'=None,
    ) -> int:
        if not self.available:
            return 0
        records: List[Dict[str, Any]] = []
        for file_path in FileManager.ListFiles(
            *self.replay_folders,
            ext='.json',
        ):
            try:
                record = self._record_from_replay(file_path)
                existing = self._existing_replay_state(str(record['source_key']))
                existing_result = existing['result']
                if existing_result in ('win', 'loss'):
                    record['result'] = existing_result
                    record['replay_analysis_status'] = existing['status']
                    record['replay_analysis_error'] = existing['error']
                elif record['result'] == 'unknown':
                    if record['rules_version'] != 'v18':
                        from game.scene.loader import UnsupportedReplayRulesError
                        record['replay_analysis_status'] = 'unsupported'
                        record['replay_analysis_error'] = UnsupportedReplayRulesError.MESSAGE
                    elif outcome_analyzer:
                        try:
                            outcome = outcome_analyzer.Analyze(file_path)
                            record.update(outcome.AsRecord())
                            record['replay_analysis_status'] = 'resolved'
                            record['replay_analysis_error'] = ''
                        except Exception as exc:
                            record['replay_analysis_status'] = 'failed'
                            record['replay_analysis_error'] = str(exc)
                            Log.Warn(
                                CATEGORY_NAME,
                                f'Could not determine replay outcome {file_path}: {exc}',
                            )
                records.append(record)
            except Exception as exc:
                Log.Warn(
                    CATEGORY_NAME,
                    f'Could not import replay {file_path}: {exc}',
                )

        # Achievement streaks and unlock timestamps depend on game order.
        # Replay folders are not guaranteed to be listed chronologically.
        records.sort(key=lambda record: str(record['finished_at']))
        imported = 0
        for record in records:
            result = self._store_game(record)
            imported += int(bool(result['inserted']))
        return imported

    @staticmethod
    def _rate(wins: int, games: int) -> float:
        return round(wins * 100.0 / games, 1) if games else 0.0

    @staticmethod
    def _normalize_source_filter(source: str) -> str:
        source = str(source or 'all').strip().lower()
        if source not in ('all', *GameHistory.KNOWN_SOURCES):
            raise ValueError('Unknown game history source filter.')
        return source

    @staticmethod
    def _normalize_physical_date(value: Any) -> str:
        text = str(value or '').strip()
        if not text:
            return GameHistory._now()
        try:
            parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError as exc:
            raise ValueError('Played date is invalid.') from exc
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()
        return parsed.isoformat()

    @staticmethod
    def _required_text(data: Dict[str, Any], key: str, label: str, limit: int) -> str:
        value = str(data.get(key, '')).strip()
        if not value:
            raise ValueError(f'{label} is required.')
        if len(value) > limit:
            raise ValueError(f'{label} is too long.')
        return value

    def SavePhysicalGame(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.available:
            raise RuntimeError('Game history is unavailable.')
        if not isinstance(data, dict):
            raise ValueError('Expected a physical game object.')

        hero_name = self._required_text(data, 'hero_name', 'Hero', 120)
        scenario_name = self._required_text(data, 'scenario_name', 'Scenario', 160)
        result = str(data.get('result', '')).strip().lower()
        if result not in ('win', 'loss'):
            raise ValueError('Result must be win or loss.')
        rounds = self._safe_int(data.get('rounds'))
        if rounds is not None and not 1 <= rounds <= 999:
            raise ValueError('Rounds must be between 1 and 999.')
        playtime_minutes = self._safe_float(data.get('playtime_minutes'))
        if playtime_minutes is not None and not 0 <= playtime_minutes <= 100000:
            raise ValueError('Play time is invalid.')
        remaining_hit_points = self._safe_int(data.get('remaining_hit_points'))
        if remaining_hit_points is not None and not 0 <= remaining_hit_points <= 999:
            raise ValueError('Remaining hit points are invalid.')
        clean_table = data.get('clean_table') is True
        notes = str(data.get('notes', '')).strip()
        if len(notes) > 4000:
            raise ValueError('Notes are too long.')
        deck_name = str(data.get('deck_name', '')).strip()
        if len(deck_name) > 200:
            raise ValueError('Deck name is too long.')

        finished_at = self._normalize_physical_date(data.get('finished_at'))
        hero_code = str(data.get('hero_code', '')).strip()[:80]
        villain_code = str(data.get('villain_code', '')).strip()[:80]
        scenario_key = str(data.get('scenario_key', '')).strip()
        if not scenario_key:
            scenario_key = self._slug(scenario_name)
        if len(scenario_key) > 160:
            raise ValueError('Scenario key is too long.')

        record = {
            'finished_at': finished_at,
            'engine_version': '',
            'rules_version': 'v18',
            'hero_code': hero_code,
            'hero_name': hero_name,
            'villain_code': villain_code,
            'villain_name': scenario_name,
            'scenario_name': scenario_name,
            'scenario_key': scenario_key,
            'expert': int(bool(data.get('expert', False))),
            'result': result,
            'game_over_reason': '',
            'rounds': rounds,
            'playtime_seconds': (
                playtime_minutes * 60 if playtime_minutes is not None else None
            ),
            'campaign_id': '',
            'game_mode': 'physical',
            'deck_name': deck_name,
            'deck_source': 'physical',
            'remaining_hit_points': remaining_hit_points,
            'minions_in_play': 0 if clean_table else None,
            'side_schemes_in_play': 0 if clean_table else None,
            # A physical session does not have the engine's Undo command.
            'undo_count': 0,
            'replay_file': '',
            'imported_from_replay': 0,
            'source': 'physical',
            'notes': notes,
        }

        game_id = self._safe_int(data.get('id'))
        if game_id is None:
            record['source_key'] = f'physical:{uuid.uuid4().hex}'
            stored = self._store_game(record)
            return {
                'id': stored['id'],
                'created': True,
                'unlocked': stored['unlocked'],
            }

        columns = (
            'finished_at', 'hero_code', 'hero_name', 'villain_code',
            'villain_name', 'scenario_name', 'scenario_key', 'expert', 'result',
            'rounds', 'playtime_seconds', 'deck_name', 'notes',
            'remaining_hit_points', 'minions_in_play',
            'side_schemes_in_play', 'undo_count',
        )
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                f'UPDATE games SET {", ".join(f"{column} = ?" for column in columns)} '
                "WHERE id = ? AND source = 'physical'",
                (*[record[column] for column in columns], game_id),
            )
            if not cursor.rowcount:
                raise ValueError('Physical game was not found.')
            unlocked = AchievementEvaluator.Recalculate(
                connection,
                game_id,
                finished_at,
            )
        return {'id': game_id, 'created': False, 'unlocked': unlocked}

    def DeletePhysicalGame(self, game_id: Any) -> Dict[str, Any]:
        parsed_id = self._safe_int(game_id)
        if parsed_id is None:
            raise ValueError('Physical game id is invalid.')
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM games WHERE id = ? AND source = 'physical'",
                (parsed_id,),
            )
            if not cursor.rowcount:
                raise ValueError('Physical game was not found.')
            AchievementEvaluator.Recalculate(connection)
        return {'deleted': True, 'id': parsed_id}

    def SaveCollection(self, product_keys: Any) -> Dict[str, Any]:
        if not isinstance(product_keys, list):
            raise ValueError('Owned products must be a list.')
        normalized: List[str] = []
        for value in product_keys:
            key = str(value).strip().lower()
            if not key or len(key) > 80 or not re.fullmatch(r'[a-z0-9_]+', key):
                raise ValueError('An owned product key is invalid.')
            if key not in normalized:
                normalized.append(key)
        now = self._now()
        with self._lock, self._connect() as connection:
            existing = {
                str(row['product_key']): str(row['owned_at'])
                for row in connection.execute(
                    'SELECT product_key, owned_at FROM collection_products'
                ).fetchall()
            }
            connection.execute('DELETE FROM collection_products')
            connection.executemany(
                'INSERT INTO collection_products '
                '(product_key, owned_at, updated_at) VALUES (?, ?, ?)',
                [(key, existing.get(key, now), now) for key in normalized],
            )
        return {'owned_products': normalized}

    @staticmethod
    def _rating_value(data: Dict[str, Any], key: str) -> int|None:
        value = data[key]
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError('Ratings must be whole numbers from 1 to 5.')
        return value

    def SaveGameRatings(self, source_key: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.available:
            raise RuntimeError('Game history is unavailable.')
        if not isinstance(data, dict):
            raise ValueError('Expected a game rating object.')

        allowed = ('hero_rating', 'scenario_rating')
        ratings = {
            key: self._rating_value(data, key)
            for key in allowed
            if key in data
        }
        if not ratings:
            raise ValueError('Choose a hero or scenario rating to save.')

        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                f'UPDATE games SET {", ".join(f"{key} = ?" for key in ratings)} '
                "WHERE source_key = ? AND source = 'digital' "
                "AND result IN ('win', 'loss')",
                (*ratings.values(), source_key),
            )
            if not cursor.rowcount:
                raise ValueError('The completed digital game was not found.')
            row = connection.execute(
                'SELECT hero_rating, scenario_rating FROM games WHERE source_key = ?',
                (source_key,),
            ).fetchone()
        assert row is not None
        return {
            'saved': True,
            'hero_rating': row['hero_rating'],
            'scenario_rating': row['scenario_rating'],
        }

    def SaveCurrentGameRatings(self, game: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        world = game.world
        scene = game.session.scene
        if not world or not scene or not world.is_game_over:
            raise ValueError('There is no completed game to rate.')
        if world.game_over.is_game_exit_or_undo:
            raise ValueError('Only a completed game can be rated.')
        if game.controller_manager.replay.is_replay or scene.is_puzzle:
            raise ValueError('Replay and puzzle sessions cannot be rated.')
        if not scene.GetMetadataBool('statistics_eligible'):
            raise ValueError('This game is not eligible for statistics.')

        source_key = f'game:{self.EnsureSceneGameId(scene)}'
        with self._lock, self._connect() as connection:
            exists = connection.execute(
                'SELECT 1 FROM games WHERE source_key = ?',
                (source_key,),
            ).fetchone() is not None
        if not exists:
            self._store_game(self._live_record(game), self._live_card_statistics(game))
        return self.SaveGameRatings(source_key, data)

    def GetDashboard(self, source: str='all') -> Dict[str, Any]:
        if not self.available:
            return {'available': False, 'error': 'Game history is unavailable.'}
        source = self._normalize_source_filter(source)
        with self._lock, self._connect() as connection:
            where = '' if source == 'all' else ' WHERE source = ?'
            parameters: tuple[Any, ...] = () if source == 'all' else (source,)
            overview_row = connection.execute(
                'SELECT '
                "SUM(CASE WHEN result IN ('win', 'loss') THEN 1 ELSE 0 END) completed, "
                "SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) wins, "
                "SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) losses, "
                "SUM(CASE WHEN result = 'unknown' THEN 1 ELSE 0 END) unknown_games, "
                "AVG(CASE WHEN result IN ('win', 'loss') THEN rounds END) average_rounds, "
                "AVG(CASE WHEN result IN ('win', 'loss') THEN playtime_seconds END) average_playtime "
                f'FROM games{where}',
                parameters,
            ).fetchone()
            completed = int(overview_row['completed'] or 0)
            wins = int(overview_row['wins'] or 0)

            def grouped(query: str) -> List[Dict[str, Any]]:
                rows: List[Dict[str, Any]] = []
                for row in connection.execute(query, parameters).fetchall():
                    item = dict(row)
                    games = int(item.pop('games'))
                    item['games'] = games
                    item['wins'] = int(item['wins'])
                    item['losses'] = games - item['wins']
                    item['win_rate'] = self._rate(item['wins'], games)
                    rows.append(item)
                return rows

            heroes = grouped(
                'SELECT hero_code, MAX(hero_name) hero_name, COUNT(*) games, '
                "SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) wins, "
                'ROUND(AVG(hero_rating), 2) average_rating, '
                'COUNT(hero_rating) rating_count '
                "FROM games WHERE result IN ('win', 'loss') "
                + ("AND source = ? " if source != 'all' else '') +
                'GROUP BY hero_code ORDER BY games DESC, hero_name'
            )
            villains = grouped(
                'SELECT MAX(villain_code) villain_code, '
                'MAX(villain_name) villain_name, COUNT(*) games, '
                "SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) wins, "
                'ROUND(AVG(scenario_rating), 2) average_rating, '
                'COUNT(scenario_rating) rating_count '
                "FROM games WHERE result IN ('win', 'loss') "
                + ("AND source = ? " if source != 'all' else '') +
                'GROUP BY scenario_key ORDER BY games DESC, villain_name'
            )
            matchups = grouped(
                'SELECT hero_code, MAX(hero_name) hero_name, '
                'MAX(villain_code) villain_code, MAX(villain_name) villain_name, expert, '
                'COUNT(*) games, '
                "SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) wins "
                "FROM games WHERE result IN ('win', 'loss') "
                + ("AND source = ? " if source != 'all' else '') +
                'GROUP BY hero_code, scenario_key, expert '
                'ORDER BY games DESC, hero_name, villain_name, expert'
            )
            recent = [dict(row) for row in connection.execute(
                'SELECT id, finished_at, hero_code, hero_name, villain_code, scenario_key, '
                'villain_name, expert, result, rounds, playtime_seconds, '
                'game_over_reason, replay_file, replay_analysis_status, '
                'replay_analysis_error, source, deck_name, notes, '
                'remaining_hit_points, minions_in_play, side_schemes_in_play, '
                'hero_rating, scenario_rating '
                'FROM games '
                + ("WHERE source = ? " if source != 'all' else '') +
                'ORDER BY datetime(finished_at) DESC, id DESC LIMIT 100',
                parameters,
            ).fetchall()]
            owned_products = [
                str(row['product_key'])
                for row in connection.execute(
                    'SELECT product_key FROM collection_products '
                    'ORDER BY product_key'
                ).fetchall()
            ]
            return {
                'available': True,
                'source_filter': source,
                'overview': {
                    'completed': completed,
                    'wins': wins,
                    'losses': int(overview_row['losses'] or 0),
                    'win_rate': self._rate(wins, completed),
                    'unknown_games': int(overview_row['unknown_games'] or 0),
                    'average_rounds': round(float(overview_row['average_rounds'] or 0), 1),
                    'average_playtime': round(float(overview_row['average_playtime'] or 0), 1),
                },
                'heroes': heroes,
                'villains': villains,
                'matchups': matchups,
                'recent_games': recent,
                'achievements': AchievementEvaluator.Dashboard(connection),
                'owned_products': owned_products,
            }
