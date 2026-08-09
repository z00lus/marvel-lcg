from core import *
import os
from aiohttp import web
from engine.device.web.server.server_base import GameServerBase

from engine.file import FileManager
from engine.lib import Json
from engine.log import Log
from game.puzzle.puzzle_data import PuzzleData
from game.game_run.game_new import NewGameDescriptor

class GameServerNewGame(GameServerBase):

    async def new_debug(self, request: web.Request) -> web.Response:
        self.game.Restart()
        return web.json_response({'result': "New game created"})

    async def new_game(self, request: web.Request) -> web.Response:
        data = request.rel_url.query.get('data', "")
        new_game = Json.LoadsAs(data, NewGameDescriptor)
        self.game.NewGame(new_game)
        return web.json_response({'result': "New game created"})

    async def active_session_status(self, request: web.Request) -> web.Response:
        return web.json_response({
            'available': self.game.HasActiveSession(),
            'live': self.game.HasLiveActiveSession(),
        })

    async def continue_game(self, request: web.Request) -> web.Response:
        from game.scene.loader import UnsupportedReplayRulesError

        try:
            result = self.game.ContinueActiveSession()
        except UnsupportedReplayRulesError as exc:
            return web.json_response({'error': str(exc)}, status=409)
        except Exception as exc:
            Log.FailedTrace("WEB", exc, no_take_as_error=True)
            return web.json_response({'error': "The active game could not be restored"}, status=500)

        if result is None:
            return web.json_response({'error': "There is no active game to continue"}, status=404)
        return web.json_response({'result': result})

    async def retry_game(self, request: web.Request) -> web.Response:
        world = self.game.world
        if not world or not world.is_game_over:
            return web.json_response({'error': "The current game is not over"}, status=409)
        if getattr(world.game_over, 'players_won', None) is not False:
            return web.json_response({'error': "Try again is available only after a defeat"}, status=409)

        import random
        previous_seed = self.game.scene.seed
        random_source = random.SystemRandom()
        new_seed = previous_seed
        while new_seed == previous_seed:
            new_seed = random_source.randrange(1, 2**31 - 1)

        self.game.Restart(new_seed)
        return web.json_response({'result': "Game restarted", 'seed': new_seed})

    async def load_replay(self, request: web.Request) -> web.Response:
        from game.scene.loader import UnsupportedReplayRulesError

        replay_file = self.FindReplayFile(Unquote(request.rel_url.query_string))
        if replay_file is None:
            return web.json_response({'error': "Replay not found"}, status=404)

        try:
            self.game.LoadReplay(replay_file)
        except UnsupportedReplayRulesError as exc:
            return web.json_response({'error': str(exc)}, status=409)
        return web.json_response({'result': "New game created"})

    async def load_replay_data(self, request: web.Request) -> web.Response:
        from game.scene.scene import Scene

        data = await request.json()
        replay_data = data.get('data', None)

        try:
            step = int(request.rel_url.query_string)
        except:
            step = None

        if replay_data is None:
            return web.json_response({'error': 'No data provided'}, status=400)

        # Process the replay_data as needed
        # Log.Print("Received replay data:", replay_data)

        from game.scene.loader import LoaderHelper, UnsupportedReplayRulesError

        scene = Json.LoadsAs(replay_data, Scene)
        try:
            LoaderHelper.EnsureSupportedReplay(scene)
        except UnsupportedReplayRulesError as exc:
            return web.json_response({'error': str(exc)}, status=409)
        if step == 0:
            state = 'Replay'
        else:
            state = 'Load'
        self.game.session.LoadScene(scene, step, state)

        return web.json_response({'result': "New game created"})

    async def save_replay_data(self, request: web.Request) -> web.Response:
        data = self.game.session.DumpSave()
        compressed_data = Json.DumpGZip(data)
        self.device_manager.AddSize("Save", len(compressed_data))
        return web.Response(body=compressed_data, content_type='application/json', headers={'Content-Encoding': 'gzip'})

    async def save_local(self, request: web.Request) -> web.Response:
        if self.game.session.scene is None:
            return web.json_response({'error': "There is no game to save"}, status=409)

        replay_file = self.game.session.SaveScene(delete_old=False)
        if replay_file is None:
            return web.json_response({'error': "Replay could not be saved"}, status=500)

        return web.json_response({
            'result': "Replay saved",
            'file': FileManager.GetBaseName(replay_file),
            'path': os.path.abspath(replay_file),
            'steps': len(self.game.scene.inputs),
        })

    def play_puzzle(self, puzzle: 'PuzzleData'):
        from game.scene.scene import Scene

        self.game.active_session_enabled = False

        def get_cards_text(cards: List[str]) -> str:
            text = ",".join(f"'{x}'" for x in cards)
            return text

        puzzle_pre_command: List[str] = []

        def append_puzzle_command(command: str, cards: List[str]) -> None:
            text = get_cards_text(cards)
            if text:
                puzzle_pre_command.append(f"{command}({text})")

        append_puzzle_command("Puzzle.CreateEncounterDeck", puzzle.encounter_deck)
        append_puzzle_command("Puzzle.CreateEncounterDiscardPile", puzzle.encounter_discard_pile)
        append_puzzle_command("Puzzle.CreateHandCards", puzzle.players[0].hand_cards)
        append_puzzle_command("Puzzle.CreatePlayerDiscardPile", puzzle.players[0].player_discard_pile)
        append_puzzle_command("Puzzle.CreatePlayerDeck", puzzle.players[0].player_deck)
        append_puzzle_command("Puzzle.CreatePlayerAdditionalDeck", puzzle.players[0].set_aside)

        puzzle_data = {
            "version": puzzle.version,
            "metadata": {
                "seed": puzzle.seed,
                "comment": puzzle.comment,
                "cover": puzzle.cover,
                "is_puzzle": True
            },
            "campaign": {
                "version": puzzle.version,
                "name": "Villain",
                "villain": puzzle.villain,
                "expert": puzzle.expert,
                "schemes": puzzle.schemes,
                "set_aside": puzzle.set_aside,
                "encounters": [],
                "encounter_sets": [],
                "modular_sets": []
            },
            "players": [
                {
                    "version": puzzle.version,
                    "name": f"Player {index}",
                    "hero": puzzle.players[index].identities,
                    "hero_deck": [],
                    "obligations": [],
                    "nemesis_set": [],
                    "set_aside": puzzle.players[index].set_aside,
                    "player_deck": []
                }
                for index in range(len(puzzle.players))
            ],
            "puzzle": puzzle_pre_command + puzzle.puzzle_command,
        }

        scene = Json.LoadsAs(Json.Dumps(puzzle_data), Scene)
        scene.UpdateVersion()

        self.game.session.LoadScene(scene, None, 'Replay')
        self.controller_manager.skip.SetSkipTo(0)

    async def load_puzzle(self, request: web.Request) -> web.Response:
        puzzle = Json.LoadAs(request.rel_url.query_string, PuzzleData, check_sum="Warn")
        self.play_puzzle(puzzle)
        return web.json_response({'result': "New game created"})

    async def new_puzzle_replay(self, request: web.Request) -> web.Response:
        from game.scene.scene import Scene

        self.game.active_session_enabled = False
        scene = Json.LoadsAs(request.rel_url.query_string, Scene)
        scene.UpdateVersion()

        self.game.session.LoadScene(scene, None, 'Replay')
        self.controller_manager.skip.SetSkipTo(0)
        return web.json_response({'result': "New game created"})

    async def new_puzzle(self, request: web.Request) -> web.Response:
        self.game.active_session_enabled = False
        puzzle = Json.LoadsAs(request.rel_url.query_string, PuzzleData)
        self.play_puzzle(puzzle)
        return web.json_response({'result': "New game created"})

    async def new_game_online(self, request: web.Request) -> web.Response:
        ip = request.query.get('ip')
        port = int(request.query.get('port', 2345))
        assert ip
        text = self.device_manager.AddOnlineSite(ip, port)
        return web.Response(text=text)

    async def new_game_lan(self, request: web.Request) -> web.Response:
        port = int(request.query.get('port', 2345))
        text = self.device_manager.AddLocalNetworkSite(port)
        return web.Response(text=text)

    @override
    def __init__(self) -> None:
        super().__init__()
        self.AddAwaitGetSecurity('/new', self.new_game)
        self.AddAwaitGetSecurity('/active_session', self.active_session_status)
        self.AddPostSecurity('/continue_game', self.continue_game)
        self.AddPostSecurity('/retry', self.retry_game)
        self.AddAwaitGetSecurity('/new_debug', self.new_debug)
        self.AddAwaitGetSecurity('/load_replay', self.load_replay)
        self.AddPostSecurity('/load_replay_data', self.load_replay_data)
        self.AddAwaitGetSecurity('/save_replay_data', self.save_replay_data)
        # Compatibility with cached clients that used GET before save_local became a POST route.
        self.AddAwaitGetSecurity('/save_local', self.save_local)
        self.AddPostSecurity('/save_local', self.save_local)
        self.AddAwaitGetSecurity('/load_puzzle', self.load_puzzle)
        self.AddAwaitGetSecurity('/new_puzzle_replay', self.new_puzzle_replay)
        self.AddAwaitGetSecurity('/new_puzzle', self.new_puzzle)
        self.AddAwaitGetSecurity('/new_game_online', self.new_game_online)
        self.AddAwaitGetSecurity('/new_game_lan', self.new_game_lan)
