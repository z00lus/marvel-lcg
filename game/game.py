from core import *
import os
from build import Build
from engine.log import Log
from engine.profile import Coverage, Profile
from engine.config import ConfigVariables
from engine.file import FileManager
from engine.device.manager import *
from game import *
from game.world import *
from game.scene import *
from game.scene.loader import SceneLoader
from game.game_run.game_new import NewGameDescriptor
from game.game_run.game_state import GameState
from game.game_run.game_session import GameSession
from game.game_run.campaign_progress import CampaignProgressStore
from game.statistics.game_statistics import GameStatistics
from game.statistics.game_history import GameHistory

CATEGORY_NAME = "GAME"

ON_STARTUP_LOAD_SAVE_FILE   = ConfigVariables.File('on_startup_load_save_file', "")
PAUSE_TEST_STATISTICS       = ConfigVariables.Bool('pause_test_statistics', True)
AUTO_SAVE_AFTER_GAME_OVER   = ConfigVariables.Bool('auto_save_after_game_over', False)
ACTIVE_SESSION_FILE         = ConfigVariables.File('active_session_file', "./save_active_session.json")

class Game:

    def __init__(
        self,
        statistics: 'GameStatistics',
        device_manager: 'DeviceManager',
        game_history: 'GameHistory|None'=None,
    ) -> None:
        from engine.controller import ControllerManager

        self.state      = GameState()
        self.session    = GameSession(self)

        self.controller_manager = ControllerManager(self, device_manager)
        self.statistics = statistics
        self.game_history = game_history
        self.active_session_enabled = False
        self.campaign_progress = CampaignProgressStore()

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
        save_new_active_session = self.active_session_enabled and self.state.start_state.is_new
        self.UpdatePauseStatistics(is_testing)

        Log.Setup()
        if not is_testing:
            Coverage.Setup()

        Tracker.ResetStats()
        setup_ok = self.session.GameSetup(self.controller_manager, self.state)
        if setup_ok and save_new_active_session:
            self.SaveActiveSession()
        return setup_ok

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
        self.active_session_enabled = True
        self.RemoveActiveSessionFile()
        self.controller_manager.replay.SetIsReplay(False)
        self.session.Restart(seed)
        self.controller_manager.OnRestart()

    def Shutdown(self):
        self.controller_manager.OnShutdown()

    ################################################################################
    # One server-side checkpoint is shared by every browser connected to this
    # server. It is intentionally separate from user-created replay files.
    @property
    def active_session_file(self) -> str:
        return ACTIVE_SESSION_FILE.value

    @property
    def active_session_temp_file(self) -> str:
        path, extension = os.path.splitext(self.active_session_file)
        return f"{path}.tmp{extension}"

    def RemoveActiveSessionFile(self) -> None:
        for file_path in [self.active_session_file, self.active_session_temp_file]:
            if FileManager.IsFile(file_path):
                FileManager.Delete(file_path)

    def HasLiveActiveSession(self) -> bool:
        return bool(
            self.active_session_enabled and
            self.state.is_running and
            self.world and
            not self.world.is_game_over and
            not self.scene.is_puzzle and
            not self.controller_manager.replay.is_replay
        )

    def HasActiveSession(self) -> bool:
        return self.HasLiveActiveSession() or FileManager.IsFile(self.active_session_file)

    def SaveActiveSession(self) -> bool:
        from game.test import Test

        if Test.IsInTesting() or not self.HasLiveActiveSession():
            return False

        try:
            saved_file = self.session.SaveScene(
                name=self.active_session_temp_file,
                delete_old=False,
            )
            if saved_file is None:
                return False

            FileManager.Replace(saved_file, self.active_session_file)
            Log.Info(CATEGORY_NAME, f"Active session saved: {self.active_session_file}")
            return True
        except Exception as exc:
            Log.FailedTrace(CATEGORY_NAME, exc, no_take_as_error=True)
            return False

    def ContinueActiveSession(self) -> Literal["live", "loaded"]|None:
        if self.HasLiveActiveSession():
            return "live"
        if not FileManager.IsFile(self.active_session_file):
            return None

        self.active_session_enabled = True
        try:
            # -1 replays every recorded choice, then stops at the saved turn
            # boundary and resumes as a normal game rather than a replay.
            self.controller_manager.replay.SetIsReplay(False)
            self.session.Load(self.active_session_file, -1, "Load")
            self.controller_manager.OnNewGame()
        except Exception:
            self.active_session_enabled = False
            raise
        return "loaded"

    def NewGame(self, new_game: 'NewGameDescriptor') -> None:
        campaign_progress = getattr(new_game, 'campaign_progress', {})
        progress_store = getattr(self, 'campaign_progress', None)
        prepared_progress = None
        if progress_store and campaign_progress:
            # Validate replacement before disturbing the current game. The
            # record itself is committed only after NewGame accepted the
            # descriptor.
            prepared_progress = progress_store.PrepareStart(campaign_progress)
            # On resume, PrepareStart deliberately keeps the server copy. Feed
            # that exact log into SceneLoader as well, so a stale browser can
            # never roll campaign state back inside the new scenario.
            new_game.campaign_log = dict(
                prepared_progress['campaign']['campaignLog'],
            )

        if self.world:
            self.world.game_over.SetExit()

        self.active_session_enabled = True
        self.RemoveActiveSessionFile()
        self.controller_manager.replay.SetIsReplay(False)
        self.session.NewGame(new_game)
        if prepared_progress:
            progress_store.CommitPreparedStart(prepared_progress)
        self.controller_manager.OnNewGame()

    def LoadReplay(self, file_path: 'str') -> None:
        self.active_session_enabled = False
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
            campaign_progress = getattr(self, 'campaign_progress', None)
            if campaign_progress:
                try:
                    campaign_progress.AdvanceGame(self)
                except Exception as exc:
                    # A persistence problem must not turn a completed game into
                    # an engine crash. The authenticated endpoint can retry the
                    # same idempotent update from the final screen.
                    Log.FailedTrace(CATEGORY_NAME, exc, no_take_as_error=True)
            if self.game_history:
                try:
                    self.game_history.RecordCompletedGame(self)
                except Exception as exc:
                    Log.FailedTrace(CATEGORY_NAME, exc, no_take_as_error=True)
            if self.active_session_enabled:
                self.active_session_enabled = False
                self.RemoveActiveSessionFile()
            self.statistics.Save()

        if self.state.start_state.is_undo:
            self.GameRestartInternal()
            return False
        elif self.state.start_state.is_in_testing:
            return False
        elif self.state.exit_state.is_normal_exit:
            self.OnExitGameInternal()

        return True
