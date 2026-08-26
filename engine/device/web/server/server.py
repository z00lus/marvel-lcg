from engine.device.web.server.server_files import GameServerFiles
from engine.device.web.server.server_html import GameServerHTML
from engine.device.web.server.server_get import GameServerGet
from engine.device.web.server.server_new_game import GameServerNewGame
from engine.device.web.server.server_marvelcdb import GameServerMarvelCdb
from engine.device.web.server.server_campaign_progress import GameServerCampaignProgress
from engine.device.web.server.server_game_history import GameServerGameHistory
from engine.device.web.server.server_proxy import GameServerProxy
from engine.device.web.server.server_agent import GameServerAgent
from engine.device.web.server.server_socket import GameServerSocket
from engine.device.web.server.server_sync import GameServerSync
from engine.device.manager.web.manager import WebDeviceManager

class GameServer(GameServerFiles, GameServerHTML, GameServerGet, GameServerNewGame, GameServerMarvelCdb, GameServerCampaignProgress, GameServerProxy, GameServerGameHistory, GameServerAgent, GameServerSocket, GameServerSync):

    def __init__(self, manager: 'WebDeviceManager') -> None:
        self.SetManager(manager)
        super().__init__()
