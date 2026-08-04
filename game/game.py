from core import *
from build import Build
from engine.log import Log
from engine.profile import Coverage, Profile
from engine.config import ConfigVariables
from engine.device.manager import *
from game import *
from game.world import *
from game.scene import *
from game.scene.loader import SceneLoader
from game.game_run.game_new import NewGameDescriptor
from game.game_run.game_state import GameState
from game.game_run.game_session import GameSession
from game.statistics.game_statistics import GameStatistics

CATEGORY_NAME = "GAME"

ON_STARTUP_LOAD_SAVE_FILE   = ConfigVariables.File('on_startup_load_save_file', "")
PAUSE_TEST_STATISTICS       = ConfigVariables.Bool('pause_test_statistics', True)
AUTO_SAVE_AFTER_GAME_OVER   = ConfigVariables.Bool('auto_save_after_game_over', False)

class Game:

    def __init__(self, statistics: 'GameStatistics', device_manager: 'DeviceManager') -> None:
        from engine.controller import ControllerManager

        self.state      = GameState()
        self.session    = GameSession(self)

        self.controller_manager = ControllerManager(self, device_manager)
        self.statistics = statistics

    @property
    def world(self) -> 'World|None':
        return self.session.world

    @property
    def scene(self) -> 'Scene':
        assert self.session.scene
        return self.session.scene

    def UpdatePauseStatistics(self, is_testing: bool):
        if self.scene.is_puzzle:
            pause = True
        elif self.session.cheat:
            pause = True
        elif is_testing:
            pause = PAUSE_TEST_STATISTICS.value
        else:
            pause = "WhenSkipping"
        self.statistics.SetPause(pause)

    def GameSetup(self) -> bool:
        from game.test import Test
        from engine.log import Log

        is_testing = Test.IsInTesting()
        self.UpdatePauseStatistics(is_testing)

        Log.Setup()
        if not is_testing:
            Coverage.Setup()

        Tracker.ResetStats()
        return self.session.GameSetup(self.controller_manager, self.state)

    def GameLoop(self):
        if self.world:
            self.world.OnGameLoop()

    def OnExitGameInternal(self):
        if self.controller_manager.skip.SetIsSkipping(False):
            if self.world:
                self.world.render.PresentForceNoWait()

        # Log.ReportStats()

        need_save = Log.HasError("VERSION", warn=True) or \
            (not self.controller_manager.skip.is_skipping and self.controller_manager.replay.current_step_id > self.controller_manager.skip.skip_to)
        need_wait_exit = (self.controller_manager.replay.current_step_id > self.controller_manager.skip.skip_to)

        if need_wait_exit and not need_save:
            need_save = True

        if need_save and AUTO_SAVE_AFTER_GAME_OVER.value:
            if not self.controller_manager.replay.is_replay and \
                not self.scene.is_puzzle:
                if Log.HasError(error=True):
                    # Continue run to save replay
                    Debug.DebugBreak()
                self.session.SaveScene(delete_old=True)
        else:
            if not Build.release:
                Log.Print(f"Scene Name: {self.scene.name}")

    def SetGameOverInternal(self):
        assert self.world
        if not self.world.game_over.is_game_exit_or_undo:
            self.world.OnGameOver(self.world.game_over)

        if not self.state.IsRunningNewGame():
            self.controller_manager.OnGameOver()
            # if show_report:
            # not self.statistics.pause
            if not Build.release:
                Log.ReportStats()
                # Coverage.Report("All")
        else:
            # Undo
            pass

    def ApplyHistoryInput(self):
        self.scene.inputs = self.controller_manager.replay.history_inputs[:]

    def GameRestartInternal(self):
        Log.Print("\n\n=== Game Restart ===")
        if self.session.preserve_replay_inputs_on_restart:
            self.session.preserve_replay_inputs_on_restart = False
        else:
            self.ApplyHistoryInput()

    def Restart(self, seed: int|None=-1) -> None:
        assert self.world
        self.world.game_over.SetExit()
        self.session.Restart(seed)
        self.controller_manager.OnRestart()

    def Shutdown(self):
        self.controller_manager.OnShutdown()

    def NewGame(self, new_game: 'NewGameDescriptor') -> None:
        if self.world:
            self.world.game_over.SetExit()

        self.session.NewGame(new_game)
        self.controller_manager.OnNewGame()

    def LoadReplay(self, file_path: 'str') -> None:
        if self.world:
            self.world.game_over.SetExit()

        self.session.Load(file_path, None, "Replay")
        self.controller_manager.OnNewGame()

    ################################################################################
    #
    def GameRun(self):
        from game.test import Test

        save_file = ON_STARTUP_LOAD_SAVE_FILE.value
        if save_file:
            scene = SceneLoader.Load(save_file, nullable=True)
            if not scene:
                scene = SceneLoader.NewScene("rhino", None, ["spider_man"], -1)
            self.session.SetScene(scene, 'Load')
        else:
            # Wait for new game
            self.state.WaitUntilGameStart()

        def run_game():
            while True:

                if Profile.Run(self.GameSetup, profile_name="Game"):
                    Profile.Run(self.GameLoop, profile_name="Game")

                if not self.SetGameOver():
                    continue
                else:
                    break

        while True:
            if not Test.Run(self):
                run_game()

            self.state.SetRunningState(False) # This means waiting for new game
            self.state.WaitUntilGameStart()

    def SetGameOver(self) -> bool:
        self.SetGameOverInternal()
        if self.state.exit_state.is_normal_exit:
            self.statistics.Save()

        if self.state.start_state.is_undo:
            self.GameRestartInternal()
            return False
        elif self.state.start_state.is_in_testing:
            return False
        elif self.state.exit_state.is_normal_exit:
            self.OnExitGameInternal()

        return True
