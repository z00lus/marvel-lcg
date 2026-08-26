from core import *
import asyncio
import os
import re

from aiohttp import web

from engine.device.web.server.server_base import GameServerBase
from engine.file import FileManager
from engine.lib import Json
from engine.log import Log
from game.game_run.game_new import NewGameDescriptor


class GameServerAgent(GameServerBase):
    """Authenticated JSON API for a single-player, non-browser controller.

    The API deliberately reuses ``DeviceManager.ask_options`` and
    ``DeviceManager.WhenInput``.  It therefore does not create a parallel rules
    path: targets, payments, timing windows, replay recording and undo all go
    through the same ``Controller.ChoiceOne`` code as browser input.
    """

    _CONTENT_ID = re.compile(r"^[a-zA-Z0-9_.-]+$")
    _ANSI = re.compile(r"\x1b\[[0-9;]*m")
    _MAX_WAIT_MS = 30000
    _DEFAULT_DECISION_WAIT_MS = 2000
    _POLL_INTERVAL_SECONDS = 0.02

    @classmethod
    def _validate_content_id(cls, value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value or not cls._CONTENT_ID.fullmatch(value):
            raise ValueError(f"Invalid {field_name}")
        return value

    @staticmethod
    def _file_id(path: str) -> str:
        return os.path.splitext(FileManager.GetBaseName(path))[0]

    @staticmethod
    def _first_card_id(values: Sequence[str]) -> str:
        if not values:
            return ""
        return str(values[0]).split(',')[0]

    @staticmethod
    def _load_json(load_type: 'FileManager.JsonType', content_id: str) -> Dict[str, Any]:
        path = FileManager.FindJsonPath(load_type, content_id, nullable=True)
        if path is None:
            raise ValueError(f"{load_type} '{content_id}' was not found")
        return Json.Load(path)

    @classmethod
    def BuildSoloGame(
        cls,
        hero_id: str,
        scenario_id: str,
        *,
        expert: bool=False,
        underling_id: str|None=None,
        seed: int=-1,
        timeout: float=0,
    ) -> NewGameDescriptor:
        hero_id = cls._validate_content_id(hero_id, "hero id")
        scenario_id = cls._validate_content_id(scenario_id, "scenario id")

        hero = cls._load_json('Hero', hero_id)
        selected_scenario_id = f"{scenario_id}_expert" if expert else scenario_id
        scenario = cls._load_json('Campaign', selected_scenario_id)

        underling_sets = list(scenario.get('underling_sets', []))
        if underling_sets:
            if underling_id is None:
                raise ValueError(
                    f"Scenario '{scenario_id}' requires an underling: "
                    + ", ".join(underling_sets)
                )
            underling_id = cls._validate_content_id(underling_id, "underling id")
            if underling_id not in underling_sets:
                raise ValueError(
                    f"Underling '{underling_id}' is not valid for scenario '{scenario_id}'"
                )
            underling = cls._load_json('EncounterSet', underling_id)
            villain_key = 'expert_villain' if expert else 'villain'
            scenario['villain'] = list(underling.get(villain_key, []))
            scenario['set_aside'] = list(scenario.get('set_aside', [])) + list(
                underling.get('set_aside', [])
            )
            scenario['encounters'] = list(scenario.get('encounters', [])) + list(
                underling.get('encounters', [])
            )

        encounter_sets = list(dict.fromkeys(
            list(scenario.get('encounter_sets', []))
            + list(scenario.get('modular_sets', []))
        ))
        return NewGameDescriptor(
            campaign_json=Json.Dumps(scenario),
            encounter_set_names=encounter_sets,
            hero_json=[Json.Dumps(hero)],
            seed=int(seed),
            timeout=float(timeout),
            challenges=[],
            rules=['v18_all'],
            campaign_log={},
            record_statistics=False,
        )

    def _catalog(self) -> Dict[str, Any]:
        from engine.file.manager import (
            SCENARIOS_FOLDERS,
            STARTER_DECK_FOLDER,
            USER_DECK_FOLDER,
        )

        starter_paths = FileManager.ListFiles(STARTER_DECK_FOLDER.value, ext='.json')
        user_paths = FileManager.ListFiles(
            USER_DECK_FOLDER.value,
            ext='.json',
            check_file_name=lambda name: not name.startswith('.'),
        )
        heroes: List[Dict[str, Any]] = []
        for path, source in [(x, 'precon') for x in starter_paths] + [
            (x, 'user') for x in user_paths
        ]:
            try:
                data = Json.Load(path)
                heroes.append({
                    'id': self._file_id(path),
                    'name': data.get('deck_name') or data.get('name') or self._file_id(path),
                    'hero_name': data.get('name', ''),
                    'hero_card_id': self._first_card_id(data.get('hero', [])),
                    'source': source,
                })
            except Exception as exc:
                Log.Debug('WEB', f"Agent catalog skipped {path}: {exc}")

        scenario_paths = FileManager.ListFiles(*SCENARIOS_FOLDERS.value, ext='.json')
        scenarios_by_id = {
            self._file_id(path): path
            for path in scenario_paths
        }
        sets_info = self._load_json('SetInfo', 'sets_info.json')
        scenario_ids = list(dict.fromkeys(
            scenario_id
            for set_name, set_info in sets_info.items()
            if re.match(r'^\d+\.', set_name)
            for scenario_id in set_info.get('scenarios', [])
            if scenario_id in scenarios_by_id
        ))
        scenarios: List[Dict[str, Any]] = []
        for content_id in scenario_ids:
            path = scenarios_by_id[content_id]
            try:
                data = Json.Load(path)
                image_source = (
                    data.get('schemes')
                    if data.get('underling_sets')
                    else data.get('villain') or data.get('schemes')
                ) or []
                scenarios.append({
                    'id': content_id,
                    'name': data.get('name') or content_id,
                    'image_card_id': self._first_card_id(image_source),
                    'expert_available': f"{content_id}_expert" in scenarios_by_id,
                    'underlings': list(data.get('underling_sets', [])),
                })
            except Exception as exc:
                Log.Debug('WEB', f"Agent catalog skipped {path}: {exc}")

        heroes.sort(key=lambda item: (item['source'] != 'user', item['name'].lower()))
        scenarios.sort(key=lambda item: item['name'].lower())
        return {'heroes': heroes, 'scenarios': scenarios}

    def _read_recent_log(self, player_id: int) -> List[str]:
        offset = self.device_manager.headless_log_offsets.get(player_id, len(Log.all_log_text))
        text = Log.all_log_text[offset:]
        self.device_manager.headless_log_offsets[player_id] = len(Log.all_log_text)
        lines = [self._ANSI.sub('', line).strip() for line in text.splitlines()]
        # Game-event lines use the stable ``>`` prefix.  Error lines are also
        # useful to an autonomous player and must not be hidden.
        useful = [
            line for line in lines
            if line.startswith('>')
            or '<ERROR>' in line
            or '<FAILED>' in line
        ]
        return useful[-200:]

    def _snapshot(self, player_id: int) -> Dict[str, Any]:
        game = self.game
        world = game.world
        manager = self.device_manager

        prompt = None
        if player_id in manager.asking_players and player_id in manager.ask_options:
            ask = manager.ask_options[player_id]
            prompt = {
                'revision': manager.ask_revisions[player_id],
                'ability_type': ask.ability_type,
                'event_name': ask.event_name,
                'prompt_text': ask.prompt_text,
                'show_cancel': ask.show_cancel,
                'options': Json.Loads(ask.options_json) if ask.options_json else [],
            }

        outcome = None
        if world and world.is_game_over:
            outcome = {
                'players_won': getattr(world.game_over, 'players_won', None),
                'reason': world.game_over.reason,
            }

        if outcome and world and not world.game_over.is_game_exit_or_undo:
            status = 'game_over'
        elif prompt is not None:
            status = 'awaiting_input'
        elif game.state.is_running:
            status = 'running'
        elif game.state.IsRunningNewGame():
            status = 'starting'
        else:
            status = 'idle'

        descriptor = asdict(world.render.descriptor) if world else None
        return {
            'status': status,
            'player_id': player_id,
            'game_id': game.session.game_id,
            'step': game.controller_manager.replay.current_step_id,
            'prompt_revision': manager.ask_revisions[player_id],
            'prompt': prompt,
            'outcome': outcome,
            'recent_log': self._read_recent_log(player_id),
            'world': descriptor,
        }

    @classmethod
    def _clamp_wait_ms(cls, value: Any, default: int=0) -> int:
        if value is None:
            value = default
        return max(0, min(int(value), cls._MAX_WAIT_MS))

    async def _wait_for_agent_state(
        self,
        player_id: int,
        *,
        wait_ms: int,
        since_revision: int|None=None,
        since_step: int|None=None,
        decision_only: bool=False,
    ) -> None:
        """Wait briefly for a stable decision instead of returning mid-effect.

        Headless games have no rendering synchronization or animation delays,
        so normal rules resolution reaches the next prompt in milliseconds.
        The deadline is only a guard for a genuinely stalled or unusually long
        operation; it is not an unconditional sleep.
        """
        if wait_ms <= 0:
            return

        deadline = asyncio.get_running_loop().time() + wait_ms / 1000
        while True:
            world = self.game.world
            if world and world.is_game_over:
                return

            current_revision = self.device_manager.ask_revisions[player_id]
            prompt_ready = player_id in self.device_manager.asking_players
            if decision_only:
                if prompt_ready and (
                    since_revision is None or current_revision != since_revision
                ):
                    return
            elif since_revision is None and since_step is None:
                if prompt_ready:
                    return
            else:
                revision_changed = (
                    since_revision is not None
                    and current_revision != since_revision
                )
                step_changed = (
                    since_step is not None
                    and self.game.controller_manager.replay.current_step_id != since_step
                )
                if revision_changed or step_changed:
                    return

            if asyncio.get_running_loop().time() >= deadline:
                return
            await asyncio.sleep(self._POLL_INTERVAL_SECONDS)

    async def connect(self, request: web.Request) -> web.Response:
        data = await request.json()
        player_id = int(data.get('player_id', 0))
        self.device_manager.AttachHeadlessPlayer(player_id)
        return web.json_response(self._snapshot(player_id))

    async def disconnect(self, request: web.Request) -> web.Response:
        data = await request.json()
        player_id = int(data.get('player_id', 0))
        self.device_manager.DetachHeadlessPlayer(player_id)
        return web.json_response({'result': 'disconnected', 'player_id': player_id})

    async def catalog(self, request: web.Request) -> web.Response:
        Unused(request)
        return web.json_response(self._catalog())

    async def start_game(self, request: web.Request) -> web.Response:
        data = await request.json()
        player_id = int(data.get('player_id', 0))
        self.device_manager.AttachHeadlessPlayer(player_id)
        previous_revision = self.device_manager.ask_revisions[player_id]
        try:
            descriptor = self.BuildSoloGame(
                data.get('hero', ''),
                data.get('scenario', ''),
                expert=bool(data.get('expert', False)),
                underling_id=data.get('underling'),
                seed=int(data.get('seed', -1)),
                timeout=float(data.get('timeout', 0)),
            )
            self.game.NewGame(descriptor)
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400)
        await self._wait_for_agent_state(
            player_id,
            wait_ms=self._clamp_wait_ms(
                data.get('wait_ms'), self._DEFAULT_DECISION_WAIT_MS,
            ),
            since_revision=previous_revision,
            decision_only=True,
        )
        return web.json_response(self._snapshot(player_id))

    async def continue_game(self, request: web.Request) -> web.Response:
        data = await request.json()
        player_id = int(data.get('player_id', 0))
        self.device_manager.AttachHeadlessPlayer(player_id)
        previous_revision = self.device_manager.ask_revisions[player_id]
        try:
            result = self.game.ContinueActiveSession(record_statistics=False)
        except Exception as exc:
            Log.FailedTrace('WEB', exc, no_take_as_error=True)
            return web.json_response({'error': str(exc)}, status=500)
        if result is None:
            return web.json_response({'error': 'There is no active game to continue'}, status=404)
        await self._wait_for_agent_state(
            player_id,
            wait_ms=self._clamp_wait_ms(
                data.get('wait_ms'), self._DEFAULT_DECISION_WAIT_MS,
            ),
            since_revision=previous_revision,
            decision_only=True,
        )
        return web.json_response(self._snapshot(player_id))

    async def observe(self, request: web.Request) -> web.Response:
        data = await request.json()
        player_id = int(data.get('player_id', 0))
        since_revision = data.get('since_revision')
        since_step = data.get('since_step')
        wait_ms = self._clamp_wait_ms(data.get('wait_ms'))
        self.device_manager.AttachHeadlessPlayer(player_id)

        await self._wait_for_agent_state(
            player_id,
            wait_ms=wait_ms,
            since_revision=int(since_revision) if since_revision is not None else None,
            since_step=int(since_step) if since_step is not None else None,
            decision_only=since_revision is not None,
        )

        return web.json_response(self._snapshot(player_id))

    async def act(self, request: web.Request) -> web.Response:
        data = await request.json()
        player_id = int(data.get('player_id', 0))
        revision = int(data.get('revision', -1))
        manager = self.device_manager

        if player_id not in manager.asking_players or player_id not in manager.ask_options:
            return web.json_response({'error': 'The engine is not waiting for this player'}, status=409)
        if revision != manager.ask_revisions[player_id]:
            return web.json_response({
                'error': 'The prompt changed before the action was submitted',
                'current_revision': manager.ask_revisions[player_id],
            }, status=409)

        effect_id = int(data.get('effect_id', 0))
        targets = [str(int(value)) for value in data.get('targets', [])]
        resources = [str(int(value)) for value in data.get('resources', [])]
        ask = manager.ask_options[player_id]
        options = Json.Loads(ask.options_json) if ask.options_json else []
        option_ids = {int(option.get('id', -1)) for option in options}
        if effect_id == 0:
            if not ask.show_cancel:
                return web.json_response({'error': 'This forced prompt cannot be skipped'}, status=400)
        elif effect_id not in option_ids:
            return web.json_response({'error': f'Effect {effect_id} is not a current option'}, status=400)

        command = Json.Dumps({
            'id': effect_id,
            'targets': targets,
            'resources': resources,
        })
        try:
            manager.WhenInput(command, player_id)
        except (KeyError, ValueError):
            return web.json_response({'error': 'The prompt was already answered'}, status=409)
        await self._wait_for_agent_state(
            player_id,
            wait_ms=self._clamp_wait_ms(
                data.get('wait_ms'), self._DEFAULT_DECISION_WAIT_MS,
            ),
            since_revision=revision,
            decision_only=True,
        )
        return web.json_response(self._snapshot(player_id))

    async def save_replay(self, request: web.Request) -> web.Response:
        Unused(request)
        if self.game.session.scene is None:
            return web.json_response({'error': 'There is no game to save'}, status=409)
        replay_file = self.game.session.SaveScene(delete_old=False)
        if replay_file is None:
            return web.json_response({'error': 'Replay could not be saved'}, status=500)
        return web.json_response({
            'result': 'Replay saved',
            'file': FileManager.GetBaseName(replay_file),
            'path': os.path.abspath(replay_file),
            'steps': len(self.game.scene.inputs),
        })

    @override
    def __init__(self) -> None:
        super().__init__()
        self.AddPostSecurity('/api/agent/connect', self.connect)
        self.AddPostSecurity('/api/agent/disconnect', self.disconnect)
        self.AddPostSecurity('/api/agent/catalog', self.catalog)
        self.AddPostSecurity('/api/agent/start', self.start_game)
        self.AddPostSecurity('/api/agent/continue', self.continue_game)
        self.AddPostSecurity('/api/agent/observe', self.observe)
        self.AddPostSecurity('/api/agent/act', self.act)
        self.AddPostSecurity('/api/agent/save-replay', self.save_replay)
