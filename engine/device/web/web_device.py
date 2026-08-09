from core import *
from game.render import *
from engine.task import TaskManager
from engine.device import *
from engine.device.web import *
from engine.device.manager.web.manager import WebDeviceManager
from engine.controller import *

CATEGORY_NAME = "WEB"

class WebDevice(OutputDevice, InputDevice):

    @override
    def __init__(self, controller: 'Controller', manager: 'WebDeviceManager') -> None:
        self.manager_web = manager

        # port = manager.port
        # ip_address = manager.ip_address
        # Log.Info(CATEGORY_NAME, f"URL: http://{ip_address}:{port}/table?p={controller.player_id}")

        super().__init__(controller, manager)

    @property
    def total_players(self) -> List[int]:
        return list(range(self.controller.manager.total_players))

    ################################################################################
    #
    @override
    def IsConnect(self) -> bool:
        if self.manager_web.CheckConnect(self.player_id):
            return True
        return False

    @override
    def IsSyncReady(self) -> bool:
        if self.manager_web.CheckSync(self):
            return True
        return False

    @override
    def IsInputReady(self) -> bool:
        async def run_tasks(i: int):
            self.manager_web.httpds[-1].WebSendRender(i, "GetInput")
        TaskManager.RunAwaitProcesses(run_tasks, self.total_players, wait_finished=False)
        # JobManager.AddJob(run_tasks, total_players, name="GetInput")
        return False

    ################################################################################
    #
    @override
    def Render(self) -> None:
        self.manager_web.httpds[-1].WebSendRender(self.controller.player_id, "WaitSync")
