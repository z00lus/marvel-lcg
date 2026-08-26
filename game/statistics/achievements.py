from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class AchievementDefinition:
    achievement_id: str
    name: str
    description: str
    target: int


ACHIEVEMENTS: Tuple[AchievementDefinition, ...] = (
    AchievementDefinition(
        'core_set_conqueror',
        'Core Set Conqueror',
        'Defeat Rhino, Klaw, and Ultron on Standard.',
        3,
    ),
    AchievementDefinition(
        'core_set_expert',
        'Core Set Expert',
        'Defeat Rhino, Klaw, and Ultron on Expert.',
        3,
    ),
    AchievementDefinition(
        'expert_hat_trick',
        'Expert Hat Trick',
        'Win three consecutive Expert games against three different villains.',
        3,
    ),
    AchievementDefinition(
        'the_hardest_road',
        'The Hardest Road',
        'Defeat Ronan the Accuser, Venom Goblin, and Magneto on any difficulty.',
        3,
    ),
    AchievementDefinition(
        'hero_mastery',
        'Hero Mastery',
        'Defeat ten different villains with the same hero.',
        10,
    ),
    AchievementDefinition(
        'perfect_record',
        'Perfect Record',
        'Win five completed games in a row.',
        5,
    ),
    AchievementDefinition(
        'against_all_odds',
        'Against All Odds',
        'Win with exactly 1 remaining hit point.',
        1,
    ),
    AchievementDefinition(
        'clean_table',
        'Clean Table',
        'Win with no minions and no side schemes remaining in play.',
        1,
    ),
    AchievementDefinition(
        'no_second_chances',
        'No Second Chances',
        'Win without using Undo.',
        1,
    ),
)


class AchievementEvaluator:
    CORE_SET = ('rhino', 'klaw', 'ultron')
    HARDEST = ('ronan_the_accuser', 'venom_goblin', 'magneto')

    @staticmethod
    def _count_set(
        connection: sqlite3.Connection,
        scenario_keys: Tuple[str, ...],
        expert: int|None,
    ) -> int:
        placeholders = ','.join('?' for _ in scenario_keys)
        query = (
            'SELECT COUNT(DISTINCT scenario_key) FROM games '
            f'WHERE is_service = 0 AND result = ? '
            f'AND scenario_key IN ({placeholders})'
        )
        parameters: List[Any] = ['win', *scenario_keys]
        if expert is not None:
            query += ' AND expert = ?'
            parameters.append(expert)
        row = connection.execute(query, parameters).fetchone()
        return int(row[0] or 0)

    @staticmethod
    def _recent_streak(
        connection: sqlite3.Connection,
        *,
        expert_only: bool,
        distinct_scenarios: bool,
        limit: int,
    ) -> int:
        rows = connection.execute(
            'SELECT result, expert, scenario_key FROM games '
            "WHERE is_service = 0 AND result IN ('win', 'loss') "
            'ORDER BY datetime(finished_at) DESC, id DESC LIMIT ?',
            (limit,),
        ).fetchall()
        count = 0
        scenarios: set[str] = set()
        for result, expert, scenario_key in rows:
            if result != 'win' or (expert_only and not expert):
                break
            if distinct_scenarios and scenario_key in scenarios:
                break
            scenarios.add(str(scenario_key))
            count += 1
        return count

    @classmethod
    def Progress(cls, connection: sqlite3.Connection) -> Dict[str, int]:
        progress: Dict[str, int] = {
            'core_set_conqueror': cls._count_set(connection, cls.CORE_SET, 0),
            'core_set_expert': cls._count_set(connection, cls.CORE_SET, 1),
            'expert_hat_trick': cls._recent_streak(
                connection,
                expert_only=True,
                distinct_scenarios=True,
                limit=3,
            ),
            'the_hardest_road': cls._count_set(connection, cls.HARDEST, None),
            'perfect_record': cls._recent_streak(
                connection,
                expert_only=False,
                distinct_scenarios=False,
                limit=5,
            ),
        }

        row = connection.execute(
            'SELECT MAX(villains) FROM ('
            'SELECT COUNT(DISTINCT scenario_key) AS villains FROM games '
            "WHERE is_service = 0 AND result = 'win' GROUP BY hero_code"
            ')'
        ).fetchone()
        progress['hero_mastery'] = int(row[0] or 0)

        progress['against_all_odds'] = int(bool(connection.execute(
            "SELECT 1 FROM games WHERE is_service = 0 AND result = 'win' "
            'AND remaining_hit_points = 1 LIMIT 1'
        ).fetchone()))
        progress['clean_table'] = int(bool(connection.execute(
            "SELECT 1 FROM games WHERE is_service = 0 AND result = 'win' "
            'AND minions_in_play = 0 AND side_schemes_in_play = 0 LIMIT 1'
        ).fetchone()))
        progress['no_second_chances'] = int(bool(connection.execute(
            "SELECT 1 FROM games WHERE is_service = 0 AND result = 'win' "
            "AND undo_count = 0 LIMIT 1"
        ).fetchone()))
        return progress

    @classmethod
    def UnlockEarned(
        cls,
        connection: sqlite3.Connection,
        game_id: int,
        unlocked_at: str,
    ) -> List[str]:
        progress = cls.Progress(connection)
        unlocked: List[str] = []
        for definition in ACHIEVEMENTS:
            if progress.get(definition.achievement_id, 0) < definition.target:
                continue
            cursor = connection.execute(
                'INSERT OR IGNORE INTO achievements '
                '(achievement_id, unlocked_at, unlocked_game_id) VALUES (?, ?, ?)',
                (definition.achievement_id, unlocked_at, game_id),
            )
            if cursor.rowcount:
                unlocked.append(definition.achievement_id)
        return unlocked

    @classmethod
    def Recalculate(
        cls,
        connection: sqlite3.Connection,
        unlocked_game_id: int|None=None,
        unlocked_at: str|None=None,
    ) -> List[str]:
        """Synchronize persisted unlocks with the current game history.

        Physical games can be corrected or deleted, so achievements cannot be
        append-only. Existing valid unlock timestamps are preserved while
        unlocks that are no longer earned are removed.
        """
        progress = cls.Progress(connection)
        earned = {
            definition.achievement_id
            for definition in ACHIEVEMENTS
            if progress.get(definition.achievement_id, 0) >= definition.target
        }
        existing = {
            str(row['achievement_id'])
            for row in connection.execute(
                'SELECT achievement_id FROM achievements'
            ).fetchall()
        }

        removed = existing - earned
        if removed:
            placeholders = ','.join('?' for _ in removed)
            connection.execute(
                f'DELETE FROM achievements WHERE achievement_id IN ({placeholders})',
                tuple(sorted(removed)),
            )

        timestamp = unlocked_at or datetime.now(timezone.utc).isoformat()
        unlocked: List[str] = []
        for achievement_id in sorted(earned - existing):
            connection.execute(
                'INSERT INTO achievements '
                '(achievement_id, unlocked_at, unlocked_game_id) VALUES (?, ?, ?)',
                (achievement_id, timestamp, unlocked_game_id),
            )
            unlocked.append(achievement_id)
        return unlocked

    @classmethod
    def Dashboard(cls, connection: sqlite3.Connection) -> List[Dict[str, Any]]:
        progress = cls.Progress(connection)
        unlocked_rows = {
            row['achievement_id']: row
            for row in connection.execute(
                'SELECT achievement_id, unlocked_at, unlocked_game_id '
                'FROM achievements'
            ).fetchall()
        }
        result: List[Dict[str, Any]] = []
        for definition in ACHIEVEMENTS:
            row = unlocked_rows.get(definition.achievement_id)
            value = min(progress.get(definition.achievement_id, 0), definition.target)
            result.append({
                'id': definition.achievement_id,
                'name': definition.name,
                'description': definition.description,
                'progress': value,
                'target': definition.target,
                'unlocked': row is not None,
                'unlocked_at': row['unlocked_at'] if row else None,
                'unlocked_game_id': row['unlocked_game_id'] if row else None,
            })
        return result
