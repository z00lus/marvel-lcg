from core import *
from engine.lib import Json
from engine.file import FileManager
from engine.device import *

from aiohttp import web
from engine.device.web.server.server_base import GameServerBase
from engine.config import ConfigVariables

READ_ONLY_FIRST_REPLAY_FOLDER   = ConfigVariables.Bool('read_only_first_replay_folder', True)
CARDS_JSON_FILE         = ConfigVariables.File('cards_json_file')
REPLAY_FOLDERS          = ConfigVariables.Folders('replay_folders')
DECK_FOLDERS            = ConfigVariables.Folders('deck_folders')
STARTER_DECK_FOLDER     = ConfigVariables.Folder('starter_deck_folder')
ENCOUNTER_SETS_FOLDERS  = ConfigVariables.Folders('encounter_sets_folders')
SCENARIOS_FOLDERS       = ConfigVariables.Folders('scenarios_folders')
CUSTOM_SCENARIOS_FOLDER = ConfigVariables.Folder('custom_scenario_folder')
PUZZLE_FOLDER           = ConfigVariables.Folder('puzzle_folder')
PUZZLE_TEST_FOLDER      = ConfigVariables.Folder('puzzle_test_folder')

class GameServerGet(GameServerBase):

    def ListFile(self, *folders: str, ext: str|None=None) -> web.Response:
        return web.json_response(FileManager.ListFiles(*folders, ext=ext))

    async def list_file(self, request: web.Request) -> web.Response:
        return self.ListFile(request.path)

    async def list_scenarios(self, request: web.Request) -> web.Response:
        return self.ListFile(*SCENARIOS_FOLDERS.value, CUSTOM_SCENARIOS_FOLDER.value)

    async def list_encounter_sets(self, request: web.Request) -> web.Response:
        return self.ListFile(*ENCOUNTER_SETS_FOLDERS.value)

    async def list_deck(self, request: web.Request) -> web.Response:
        return self.ListFile(*DECK_FOLDERS.value, ext=".json")

    async def list_starter_deck(self, request: web.Request) -> web.Response:
        return self.ListFile(STARTER_DECK_FOLDER.value)

    async def list_replay_files(self, request: web.Request) -> web.Response:
        if READ_ONLY_FIRST_REPLAY_FOLDER.value:
            return self.ListFile(REPLAY_FOLDERS.value[0], ext=".json")
        else:
            return self.ListFile(*REPLAY_FOLDERS.value, ext=".json")

    async def list_puzzle_files(self, request: web.Request) -> web.Response:
        return self.ListFile(PUZZLE_FOLDER.value)

    async def list_puzzle_test_files(self, request: web.Request) -> web.Response:
        return self.ListFile(PUZZLE_TEST_FOLDER.value)

    def ReadReplayFile(self, file_path: str) -> web.Response:
        from game.scene.scene import Scene
        replay, checksum = Json.LoadAsInternal(file_path, Scene)
        return web.json_response({
            "version": replay.version,
            "is_puzzle": replay.is_puzzle,
            "time": replay.time,
            "cover": replay.cover,
            "path": replay.path,
            "comment": replay.comment,
            "villain": replay.campaign.villain[0] if replay.campaign.villain else replay.campaign.schemes[0],
            "players": [x.hero[0] for x in replay.players],
            "seed": replay.seed,
            "checksum": checksum == "Ok",
            "author": "",
            "step": len(replay.inputs),
        })

    def ReadPuzzleFile(self, file_path: str) -> web.Response:
        from engine.device.web.server.server_new_game import PuzzleData
        puzzle, checksum = Json.LoadAsInternal(file_path, PuzzleData)
        return web.json_response({
            "version": puzzle.version,
            "is_puzzle": True,
            "time": "",
            "cover": puzzle.cover,
            "path": file_path,
            "comment": puzzle.comment,
            "villain": puzzle.villain[0],
            "players": [puzzle.players[0].identities[0]],
            "seed": puzzle.seed,
            "checksum": checksum == "Ok",
            "author": puzzle.author,
            "step": 0,
        })

    async def read_file(self, request: web.Request) -> web.Response:
        file = request.rel_url.query_string
        return self.ReadJsonFile(file)

    async def get_encounter_set_json(self, request: web.Request) -> web.Response:
        path = request.rel_url.query_string
        file = FileManager.FindJsonPath("EncounterSet", path)
        return self.ReadJsonFile(file)

    async def get_scenario_json(self, request: web.Request) -> web.Response:
        path = request.rel_url.query_string
        file = FileManager.FindJsonPath("Campaign", path)
        return self.ReadJsonFile(file)

    async def get_hero_json(self, request: web.Request) -> web.Response:
        path = request.rel_url.query_string
        file = FileManager.FindJsonPath("Hero", path)
        return self.ReadJsonFile(file)

    async def get_sets_json(self, request: web.Request) -> web.Response:
        file = FileManager.FindJsonPath("SetInfo", "sets_info.json")
        return self.ReadJsonFile(file)

    async def get_sets_custom_scenario(self, request: web.Request) -> web.Response:
        files = FileManager.ListFiles(CUSTOM_SCENARIOS_FOLDER.value, ".json")
        return web.json_response(files)

    async def get_cards_json(self, request: web.Request) -> web.Response:
        return self.ReadJsonFile(CARDS_JSON_FILE.value)

    async def get_translate_json(self, request: web.Request) -> web.Response:
        from engine.lib import TransText
        return self.ReadJsonFile(TransText.translate_file)

    async def get_card_json(self, request: web.Request) -> web.Response:
        from cards.database import CardsDB
        name = request.rel_url.query_string
        paper = CardsDB.FindCardPaper(name)
        return web.json_response(paper)

    async def get_completion_rate(self, request: web.Request) -> web.Response:
        return web.Response(text=str(self.game.statistics.completion_rate))

    async def get_statistics(self, request: web.Request) -> web.Response:
        return web.json_response(self.game.statistics.content.data)

    async def get_session_statistics(self, request: web.Request) -> web.Response:
        return web.json_response(self.game.session.statistics.dic)

    async def get_play_scene_name(self, request: web.Request) -> web.Response:
        controller = self.get_first_controller(request)
        if controller.world:
            text = controller.world.scene.name
        else:
            text = ""
        return web.Response(text=text)

    async def get_max_timeout(self, request: web.Request) -> web.Response:
        return web.Response(text=str(self.device_manager.timer.max_timeout))

    async def get_puzzle_json(self, request: web.Request) -> web.Response:
        path = request.rel_url.query_string
        file = FileManager.FindJsonPath("Puzzle", path)
        assert file
        return self.ReadPuzzleFile(file)

    async def get_replay_json(self, request: web.Request) -> web.Response:
        file = self.FindReplayFile(Unquote(request.rel_url.query_string))
        if file is None:
            return web.json_response({'error': "Replay not found"}, status=404)
        return self.ReadReplayFile(file)

    async def download_replay(self, request: web.Request) -> web.Response:
        requested_file = request.query.get('file', '')
        file = self.FindReplayFile(requested_file)
        if file is None:
            return web.json_response({'error': "Replay not found"}, status=404)

        from urllib.parse import quote
        with FileManager.OpenFile(file, read=True, bin=True) as replay:
            data = replay.Read()

        file_name = FileManager.GetBaseName(file)
        headers = {
            'Content-Disposition': f"attachment; filename*=UTF-8''{quote(file_name)}",
            'Cache-Control': 'no-store',
        }
        return web.Response(body=data, content_type='application/json', headers=headers)

    async def get_gamers(self, request: web.Request) -> web.Response:
        if self.controller_manager.game.state.is_running:
            num = str(self.controller_manager.total_players)
        else:
            num = "0"
        return web.Response(text=num)

    @override
    def __init__(self) -> None:
        super().__init__()
        self.AddAwaitGetSecurity('/list_file', self.list_file)
        self.AddAwaitGetSecurity('/list_scenarios', self.list_scenarios)
        self.AddAwaitGetSecurity('/list_encounter_sets', self.list_encounter_sets)
        self.AddAwaitGetSecurity('/list_deck', self.list_deck)
        self.AddAwaitGetSecurity('/list_starter_deck', self.list_starter_deck)
        self.AddAwaitGetSecurity('/list_replay_files', self.list_replay_files)
        self.AddAwaitGetSecurity('/list_puzzle_files', self.list_puzzle_files)
        self.AddAwaitGetSecurity('/list_puzzle_test_files', self.list_puzzle_test_files)
        
        self.AddAwaitGetSecurity('/read_file', self.read_file)
        self.AddAwaitGetSecurity('/get_encounter_set_json', self.get_encounter_set_json)
        self.AddAwaitGetSecurity('/get_scenario_json', self.get_scenario_json)
        self.AddAwaitGetSecurity('/get_hero_json', self.get_hero_json)
        self.AddAwaitGetSecurity('/get_sets_json', self.get_sets_json)
        self.AddAwaitGetSecurity('/get_sets_custom_scenario', self.get_sets_custom_scenario)
        self.AddAwaitGetSecurity('/get_cards_json', self.get_cards_json)
        self.AddAwaitGetSecurity('/get_translate_json', self.get_translate_json)
        self.AddAwaitGetSecurity('/get_card_json', self.get_card_json)
        self.AddAwaitGetSecurity('/get_completion_rate', self.get_completion_rate)
        self.AddAwaitGetSecurity('/get_statistics', self.get_statistics)
        self.AddAwaitGetSecurity('/get_session_statistics', self.get_session_statistics)
        self.AddAwaitGetSecurity('/get_play_scene_name', self.get_play_scene_name)
        self.AddAwaitGetSecurity('/get_max_timeout', self.get_max_timeout)
        self.AddAwaitGetSecurity('/get_puzzle_json', self.get_puzzle_json)
        self.AddAwaitGetSecurity('/get_replay_json', self.get_replay_json)
        self.AddAwaitGetSecurity('/download_replay', self.download_replay)

        self.AddAwaitGetSecurity('/get_gamers', self.get_gamers)
