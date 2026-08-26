from core import *
from engine.device import *
from engine.controller import *
from engine.log import Log

CATEGORY_NAME = "DEVICE_MANAGER"

@dataclass
class AskOptionPayload:
    options_json    : str # json
    ability_type    : str
    event_name      : str
    prompt_text     : str
    show_cancel     : bool
    replay_input    : str
    input_json      : str = field(default="{}") # client input result

class DeviceManager:

    def __init__(self) -> None:
        from engine.device.manager.timer import Timer
        from engine.device.manager.notifier import SynchronizationNotifier
        self.timer = Timer()

        self.asking_players: List[int] = [] # 0,1,2,3
        self.ask_options: Dict[int, AskOptionPayload] = {}
        # A monotonically increasing identifier for each player's prompt.  It
        # lets non-UI clients reject a command prepared for an older decision
        # window instead of accidentally applying it to the next one.
        self.ask_revisions: List[int] = [0] * 4

        self.notify = SynchronizationNotifier()

        self.controllers: List['Controller'] = []

    ################################################################################
    #
    def CreateDevices(self, controller: 'Controller') -> Tuple['OutputDevice', 'InputDevice']:
        ...

    def AddController(self, controller: 'Controller'):
        self.controllers.append(controller)

    ################################################################################
    #
    def OnNewGame(self):
        Log.DebugSilent(CATEGORY_NAME, "DeviceManager new game")
        self.ExitWait()
        self.notify.RefreshExitWait()

    def OnRestart(self):
        Log.DebugSilent(CATEGORY_NAME, "DeviceManager restart")
        self.ExitWait()

    def OnShutdown(self):
        Log.DebugSilent(CATEGORY_NAME, "DeviceManager Shutdown")
        self.ExitWait()

    ################################################################################
    #
    def ExitWait(self):
        self.asking_players = []
        self.notify.ExitWait()

    def WhenInput(self, post_json: str, player_id: int):
        self.asking_players.remove(player_id)
        self.ask_options[player_id].options_json = ""
        self.ask_options[player_id].input_json = post_json
        self.notify.WhenInput()

    def AfterSync(self):
        self.notify.RefreshExitWait()

    ################################################################################
    #
    def DoWaitConnect(self, player_id: int, check: Callable[[], bool]):
        def check_fn():
            if self.notify.should_exit_wait:
                return True
            return check()

        self.notify.connect.Wait(check_fn, None)
        # Log.Info(CATEGORY_NAME, f"[Client] Player {self.player_id} Connect")
        return

    def DoGetInput(self, data: 'AskOptionPayload', player_id: int, check: Callable[[], bool]):
        from core.lib import Time

        self.notify.RefreshExitWait()
        self.ask_options[player_id] = data
        self.ask_revisions[player_id] += 1
        self.asking_players.append(player_id)
        self.notify.has_client_input = False

        wait = self.timer.max_timeout
        if wait <= 0:
            wait = None
        self.timer.start_time = Time.GetTime()

        def check_fn():
            if self.notify.should_exit_wait:
                return True
            if self.asking_players == []:
                return True
            ask_option = self.ask_options[player_id]
            if ask_option.input_json != "{}":
                return True

            return check()

        no_time_out = self.notify.input.Wait(check_fn, wait)
        if not no_time_out:
            self.asking_players.remove(player_id)

        self.timer.start_time = None
        self.notify.has_client_input = False

        if player_id in self.asking_players:
            self.asking_players.remove(player_id)
            # When anyone has inputted, process it first
            return None

        input_json = self.ask_options[player_id].input_json
        return input_json

    def DoWaitSync(self, player_id: int, check: Callable[[], bool]):
        from core.lib import Time
        Log.DebugSilent("SYNC", f"WaitSync start")
        wait = self.timer.max_timeout
        if wait <= 0:
            wait = None
        self.timer.start_time = Time.GetTime()

        def check_fn():
            if self.notify.should_exit_wait:
                Log.DebugSilent("SYNC", f"WaitSync Exit: Force")
                return True
            return check()

        self.notify.sync.Wait(check_fn, wait)

        self.timer.start_time = None
        self.notify.has_client_input = False
        Log.DebugSilent("SYNC", f"WaitSync end")
