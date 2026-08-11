from core import *

from datetime import datetime, timezone
import os
import threading

from engine.config import ConfigVariables
from engine.file import FileManager
from engine.lib import Json


CAMPAIGN_PROGRESS_FILE = ConfigVariables.File(
    'campaign_progress_file',
    './save_campaign_progress.json',
)


CAMPAIGN_SCENARIOS: Dict[str, List[str]] = {
    'rise_of_red_skull': [
        'crossbones', 'absorbing_man', 'taskmaster', 'zola', 'red_skull',
    ],
    'galaxys_most_wanted': [
        'brotherhood_of_badoon', 'infiltrate_the_museum',
        'escape_the_museum', 'nebula', 'ronan',
    ],
    'mad_titans_shadow': [
        'ebony_maw', 'the_tower_defense', 'thanos', 'hela', 'loki',
    ],
    'sinister_motives': [
        'sandman', 'venom', 'mysterio', 'sinister_six', 'venom_goblin',
    ],
    'mutant_genesis': [
        'sabretooth', 'project_wideawake', 'master_mold',
        'mansion_attack', 'magneto',
    ],
    'next_evolution': [
        'morlock_siege', 'on_the_run', 'juggernaut', 'mister_sinister',
        'stryfe',
    ],
    'age_of_apocalypse': [
        'unus', 'four_horsemen', 'apocalypse', 'dark_beast',
        'en_sabah_nur',
    ],
    'agents_of_shield': [
        'black_widow', 'batroc', 'modok', 'thunderbolts', 'baron_zemo',
    ],
}


class CampaignProgressConflict(ValueError):
    pass


class CampaignProgressStore:
    """Own the one solo campaign that can be continued on this server.

    This is intentionally separate from ``save_active_session.json``. The
    active-session file checkpoints one game in progress, while this record is
    the state carried between the five scenarios of a campaign.
    """

    VERSION = 1

    def __init__(self, file_path: str|None=None) -> None:
        self.file_path = file_path or CAMPAIGN_PROGRESS_FILE.value
        path, extension = os.path.splitext(self.file_path)
        self.temp_file_path = f'{path}.tmp{extension}'
        self._lock = threading.RLock()

    @staticmethod
    def _Now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _RequireDict(value: Any, name: str) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError(f'{name} must be an object.')
        return value

    @staticmethod
    def _RequireString(value: Any, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'{name} is required.')
        return value.strip()

    @classmethod
    def _ValidateCampaign(cls, value: Any) -> Dict[str, Any]:
        data = cls._RequireDict(value, 'campaign')
        if data.get('version') != cls.VERSION:
            raise ValueError('Unsupported campaign progress version.')

        campaign_id = cls._RequireString(data.get('campaignId'), 'campaignId')
        scenarios = CAMPAIGN_SCENARIOS.get(campaign_id)
        if scenarios is None:
            raise ValueError(f'Unknown campaign: {campaign_id}')

        scenario_index = data.get('scenarioIndex')
        if not isinstance(scenario_index, int) or isinstance(scenario_index, bool):
            raise ValueError('scenarioIndex must be an integer.')
        if not 0 <= scenario_index < len(scenarios):
            raise ValueError('scenarioIndex is outside this campaign.')

        hero_id = cls._RequireString(data.get('heroId'), 'heroId')
        campaign_log = cls._RequireDict(data.get('campaignLog'), 'campaignLog')
        if any(not isinstance(key, str) or not isinstance(item, str)
               for key, item in campaign_log.items()):
            raise ValueError('campaignLog must contain string values.')

        completed = data.get('completed')
        if not isinstance(completed, bool):
            raise ValueError('completed must be a boolean.')

        updated_at = data.get('updatedAt')
        if updated_at is not None and not isinstance(updated_at, str):
            raise ValueError('updatedAt must be a string.')

        return {
            'version': cls.VERSION,
            'campaignId': campaign_id,
            'scenarioIndex': scenario_index,
            'heroId': hero_id,
            'campaignLog': dict(campaign_log),
            'completed': completed,
            'updatedAt': updated_at or cls._Now(),
        }

    @classmethod
    def _ValidateActiveRun(
        cls,
        value: Any,
        campaign: Dict[str, Any],
        *,
        nullable: bool=False,
    ) -> Dict[str, Any]|None:
        if value is None and nullable:
            return None

        data = cls._RequireDict(value, 'activeRun')
        if data.get('version') != cls.VERSION:
            raise ValueError('Unsupported active campaign run version.')

        campaign_id = cls._RequireString(data.get('campaignId'), 'campaignId')
        scenario_id = cls._RequireString(data.get('scenarioId'), 'scenarioId')
        scenario_name = cls._RequireString(data.get('scenarioName'), 'scenarioName')
        scenario_index = data.get('scenarioIndex')
        if not isinstance(scenario_index, int) or isinstance(scenario_index, bool):
            raise ValueError('scenarioIndex must be an integer.')

        expected_scenarios = CAMPAIGN_SCENARIOS[campaign['campaignId']]
        if (
            campaign_id != campaign['campaignId'] or
            scenario_index != campaign['scenarioIndex'] or
            scenario_id != expected_scenarios[scenario_index]
        ):
            raise ValueError('The active run does not match campaign progress.')

        return {
            'version': cls.VERSION,
            'campaignId': campaign_id,
            'scenarioId': scenario_id,
            'scenarioName': scenario_name,
            'scenarioIndex': scenario_index,
        }

    @classmethod
    def _ValidateRecord(cls, value: Any) -> Dict[str, Any]:
        record = cls._RequireDict(value, 'campaign progress')
        campaign = cls._ValidateCampaign(record.get('campaign'))
        active_run = cls._ValidateActiveRun(
            record.get('activeRun'),
            campaign,
            nullable=True,
        )
        return {'campaign': campaign, 'activeRun': active_run}

    def _LoadUnlocked(self) -> Dict[str, Any]|None:
        if not FileManager.IsFile(self.file_path):
            return None
        # This small runtime record has its own schema version and no game-data
        # checksum. Reading the text directly avoids coupling it to Ver.Initialize
        # (important during early startup and isolated persistence tests).
        with FileManager.OpenFile(self.file_path, read=True) as file:
            return self._ValidateRecord(Json.Loads(file.Read()))

    def Load(self) -> Dict[str, Any]|None:
        with self._lock:
            return self._LoadUnlocked()

    def _SaveUnlocked(self, record: Dict[str, Any]) -> None:
        folder = FileManager.GetDirName(self.file_path)
        FileManager.MakeDir(folder)
        Json.Save(record, self.temp_file_path)
        FileManager.Replace(self.temp_file_path, self.file_path)

    def PrepareStart(self, value: Any) -> Dict[str, Any]:
        request = self._RequireDict(value, 'campaignProgress')
        incoming = self._ValidateCampaign(request.get('campaign'))
        active_run = self._ValidateActiveRun(request.get('activeRun'), incoming)
        replace = request.get('replace', False)
        if not isinstance(replace, bool):
            raise ValueError('replace must be a boolean.')
        if incoming['completed']:
            raise ValueError('A completed campaign cannot start another scenario.')

        with self._lock:
            existing_record = self._LoadUnlocked()
            if existing_record and not replace:
                existing = existing_record['campaign']
                matching_fields = ('campaignId', 'scenarioIndex', 'heroId')
                if any(existing[key] != incoming[key] for key in matching_fields):
                    raise CampaignProgressConflict(
                        'Starting this campaign would replace the active campaign.',
                    )
                if existing['completed']:
                    raise CampaignProgressConflict('This campaign is already complete.')
                # The server copy is authoritative on resume. Only the active
                # scenario marker comes from the new-game request.
                incoming = existing

            return {
                'campaign': {
                    **incoming,
                    'updatedAt': self._Now(),
                },
                'activeRun': active_run,
            }

    def CommitPreparedStart(self, record: Dict[str, Any]) -> Dict[str, Any]:
        record = self._ValidateRecord(record)
        with self._lock:
            self._SaveUnlocked(record)
        return record

    def Start(self, value: Any) -> Dict[str, Any]:
        return self.CommitPreparedStart(self.PrepareStart(value))

    def Migrate(self, value: Any) -> Tuple[Dict[str, Any], bool]:
        request = self._RequireDict(value, 'campaign migration')
        campaign = self._ValidateCampaign(request.get('campaign'))
        active_run = self._ValidateActiveRun(
            request.get('activeRun'),
            campaign,
            nullable=True,
        )
        record = {'campaign': campaign, 'activeRun': active_run}

        with self._lock:
            existing = self._LoadUnlocked()
            if existing:
                return existing, False
            record['campaign']['updatedAt'] = self._Now()
            self._SaveUnlocked(record)
            return record, True

    def AdvanceVerified(
        self,
        *,
        campaign_id: str,
        scenario_name: str,
        campaign_log: Dict[str, str],
        game_over: bool,
        players_won: bool|None,
        is_replay: bool,
    ) -> Dict[str, Any]:
        with self._lock:
            record = self._LoadUnlocked()
            if record is None:
                return {'campaign': None, 'advanced': False, 'reason': 'no_campaign'}

            campaign = record['campaign']
            active_run = record['activeRun']
            if active_run is None:
                return {
                    'campaign': campaign,
                    'advanced': False,
                    'reason': 'already_recorded',
                }
            if is_replay:
                return {
                    'campaign': campaign,
                    'advanced': False,
                    'reason': 'replay',
                }
            if not game_over or players_won is not True:
                return {
                    'campaign': campaign,
                    'advanced': False,
                    'reason': 'not_victory',
                }
            if (
                campaign_id != campaign['campaignId'] or
                campaign_id != active_run['campaignId'] or
                scenario_name != active_run['scenarioName'] or
                active_run['scenarioIndex'] != campaign['scenarioIndex']
            ):
                raise CampaignProgressConflict(
                    'The completed game does not match the active campaign scenario.',
                )

            scenarios = CAMPAIGN_SCENARIOS[campaign_id]
            scenario_index = active_run['scenarioIndex']
            completed = scenario_index == len(scenarios) - 1
            campaign = {
                **campaign,
                'scenarioIndex': scenario_index if completed else scenario_index + 1,
                'campaignLog': {
                    **campaign['campaignLog'],
                    **campaign_log,
                },
                'completed': completed,
                'updatedAt': self._Now(),
            }
            record = {'campaign': campaign, 'activeRun': None}
            self._SaveUnlocked(record)
            return {'campaign': campaign, 'advanced': True, 'reason': 'victory'}

    def AdvanceGame(self, game: 'Game') -> Dict[str, Any]:
        world = game.world
        if (
            not world or
            not world.rule.mode_campaign.val or
            not world.scene.campaign.campaign_id
        ):
            record = self.Load()
            return {
                'campaign': record['campaign'] if record else None,
                'advanced': False,
                'reason': 'not_campaign_game',
            }

        from game.operate.campaign_logs import CampaignLog

        game_over = world.is_game_over
        players_won = getattr(world.game_over, 'players_won', None) if game_over else None
        campaign_log = CampaignLog.Export(
            world,
            include_remaining_hit_points=players_won is True,
        )
        return self.AdvanceVerified(
            campaign_id=world.scene.campaign.campaign_id,
            scenario_name=world.scene.campaign.name,
            campaign_log=campaign_log,
            game_over=game_over,
            players_won=players_won,
            is_replay=game.controller_manager.replay.is_replay,
        )
