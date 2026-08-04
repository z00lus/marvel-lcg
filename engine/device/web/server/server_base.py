from core import *
import os
from engine.network import WebServer
from aiohttp import web
from engine.device.manager.web.manager import WebDeviceManager
from engine.controller import *
from engine.config import ConfigVariables
from engine.file import FileManager

REPLAY_FOLDERS = ConfigVariables.Folders('replay_folders', ["./replays/"])

class GameServerBase(WebServer):

    def __init__(self) -> None:
        super().__init__()

    def SetManager(self, manager: 'WebDeviceManager'):
        self.device_manager = manager

    def get_player_ids(self, request: web.Request) -> List[int]:
        is_hot_seat = 'hot_seat' in request.rel_url.query
        if is_hot_seat:
            manager = self.controller_manager
            return list(range(manager.total_players))

        p = request.query.get('p', '0')
        if p == '':
            return [0]

        player_ids = p.split(',')
        if player_ids:
            player_ids = [int(id) for id in player_ids]
        else:
            player_ids = [0]
        return player_ids

    def get_first_controller(self, request: web.Request) -> 'Controller':
        player_ids = self.get_player_ids(request)
        player_id = player_ids[0]
        return self.device_manager.controllers[player_id]

    def FindReplayFile(self, requested_file: str) -> str|None:
        requested_file = os.path.normpath(requested_file)
        requested_name = FileManager.GetBaseName(requested_file)

        for replay_file in FileManager.ListFiles(*REPLAY_FOLDERS.value, ext=".json"):
            normalized_replay = os.path.normpath(replay_file)
            if normalized_replay == requested_file or \
                (requested_file == requested_name and FileManager.GetBaseName(normalized_replay) == requested_name):
                return replay_file
        return None

    @property
    def controller_manager(self):
        controller = self.device_manager.controllers[0]
        return controller.manager

    @property
    def game(self):
        controller = self.device_manager.controllers[0]
        return controller.game
