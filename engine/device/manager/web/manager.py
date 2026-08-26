from core import *
from engine.config import ConfigVariables
from engine.log import Log
from engine.device import *
from engine.controller import *
from engine.device.manager.web.client import ClientManager
from engine.network.net_lib import NetLib

IP                  = ConfigVariables.Str('ip', "")
PORT                = ConfigVariables.Int('port', 2345)
SERVER_ADDRESSES    = ConfigVariables.ListStr('server_addresses', [
    "127.0.0.1:2345"
])

CATEGORY_NAME = "WEB_DEVICE_MANAGER"

class WebDeviceManager(DeviceManager):

    def __init__(self) -> None:
        from engine.device.web.server.server import GameServer
        from engine.marvelcdb import MarvelCdbDeckSync

        super().__init__()

        self.client_manager = ClientManager()
        # Headless agents use the same Controller input contract as the web UI,
        # but do not need a browser or a WebSocket.  While attached they count
        # as a connected, immediately-synchronised client; decisions still pass
        # through DeviceManager.WhenInput and all normal engine validation.
        self.headless_players: Set[int] = set()
        self.headless_log_offsets: Dict[int, int] = {}
        self.httpds : List[GameServer] = []
        self.marvelcdb_deck_sync = MarvelCdbDeckSync()

        server_addresses    = SERVER_ADDRESSES.value[:]
        port                = PORT.value
        ip_address          = IP.value
        if ip_address and port:
            if ':' in ip_address:
                server_addresses.append(f"[{ip_address}]:{port}")
            else:
                server_addresses.append(f"{ip_address}:{port}")

        for server_address in set(server_addresses):

            ip_port = NetLib.ExtractIpAndPort(server_address)
            if not ip_port:
                Log.Warn(CATEGORY_NAME, f"{server_address} is invalid")
                continue

            ip, port = ip_port
            if not NetLib.IsPortAvailable(ip, port):
                raise RuntimeError(
                    f"Cannot start Marvel Champions Digital: Ronin Edition: "
                    f"{ip}:{port} is already in use. "
                    "Stop the previous instance and try again."
                )

            self.httpds.append(GameServer(self))
            self.httpds[-1].Run(ip, port, "Server")

        self.marvelcdb_deck_sync.Start()

        self.stat_sent_size: Dict[str, int] = {}

    @override
    def CreateDevices(self, controller: 'Controller') -> Tuple['OutputDevice', 'InputDevice']:
        from engine.device.web import WebDevice
        device = WebDevice(controller, self)
        return device, device

    @override
    def OnNewGame(self):
        super().OnNewGame()
        self.client_manager.ClearSync()
        self.stat_sent_size = {}

    @override
    def OnShutdown(self):
        super().OnShutdown()
        self.marvelcdb_deck_sync.Stop()
        for httpd in self.httpds:
            httpd.Shutdown()

    ################################################################################
    #
    def HasRunSite(self, ip: str, port: int) -> bool:
        for httpd in self.httpds:
            if httpd.ip == ip and httpd.port == port:
                return True
        return False

    def AddNewSiteInternal(self, ip: str, port: int) -> bool:
        from engine.device.web.server.server import GameServer
        if not self.HasRunSite(ip, port):
            httpd = GameServer(self)
            httpd.Run(ip, port, "Server")
            self.httpds.append(httpd)
            return True
        return False

    def AddLocalNetworkSite(self, port: int) -> str|None:
        ips = NetLib.ListLocalIpAddresses()
        for ip in ips:
            if ip.startswith("192.168"):
                self.AddNewSiteInternal(ip, port)
                return f"{ip}:{port}"
        assert False

    def AddOnlineSite(self, ip: str, port: int) -> str:
        self.AddLocalNetworkSite(port)
        self.AddNewSiteInternal(ip, port)
        return f"{ip}:{port}"

    ################################################################################
    #
    def KillConnect(self):
        self.client_manager.RemoveAll()
        Log.Debug(CATEGORY_NAME, "Kill Connects")

    def AttachHeadlessPlayer(self, player_id: int) -> None:
        if player_id < 0 or player_id >= len(self.controllers):
            raise ValueError(f"Player {player_id} is not available")
        if player_id not in self.headless_players:
            from engine.log import Log
            self.headless_log_offsets[player_id] = len(Log.all_log_text)
        self.headless_players.add(player_id)
        self.notify.connect.NotifyAll()
        self.notify.sync.NotifyAll()

    def DetachHeadlessPlayer(self, player_id: int) -> None:
        self.headless_players.discard(player_id)
        self.headless_log_offsets.pop(player_id, None)

    def IsHeadlessPlayer(self, player_id: int) -> bool:
        return player_id in self.headless_players

    def CheckSync(self, device: 'Device') -> bool:
        if self.IsHeadlessPlayer(device.player_id):
            return True
        # num = 1 if Game.run.controller_manager.replay.is_replay else Game.run.controller_manager.total_players
        # All players are eliminate
        if not device.is_connected:
            Log.DebugSilent("SYNC", f"WaitSync Exit: disconnected")
            return True

        player_id = device.player_id
        controller = device.controller
        if not controller.world:
            Log.DebugSilent("SYNC", f"WaitSync Exit: not world")
            return True

        if not controller.game.state.is_running:
            Log.DebugSilent("SYNC", f"WaitSync Exit: not running")
            return True

        if self.client_manager.client_synced[player_id] >= controller.world.render.last_render_id:
            Log.DebugSilent("SYNC", f"WaitSync Exit: Sync {controller.world.render.last_render_id}")
            return True

        Log.DebugSilent("SYNC", f"WaitSync Exit: Failed")
        return False

    def ClientUpdateRenderId(self, player_id: int, render_id: int, game_id: int) -> None:
        if player_id >= len(self.controllers):
            return
        if game_id == self.controllers[player_id].game.session.game_id:
            self.client_manager.client_synced[player_id] = render_id
            self.notify.sync.NotifyAll()

    def CheckConnect(self, player_id: int) -> bool:
        if self.IsHeadlessPlayer(player_id):
            return True
        def check_client_synced():
            if self.client_manager.GetClients(player_id) == []:
                return False
            return True
        return check_client_synced()

    ################################################################################
    #
    def AddSize(self, category: str, byte_size: int):
        if category not in self.stat_sent_size:
            self.stat_sent_size[category] = 0
        self.stat_sent_size[category] += byte_size
        size_mb = self.stat_sent_size[category] / (1024 * 1024)
        Log.DebugSilent(CATEGORY_NAME, f"Size: [{category}] {size_mb:.2f} MB ({byte_size})")
