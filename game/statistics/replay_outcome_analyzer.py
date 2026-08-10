from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Dict

from build import Build
from engine.device.base.input import InputDevice
from engine.device.console.console import ConsoleDevice
from engine.device.manager.base import AskOptionPayload, DeviceManager
from engine.log import Log
from engine.log.log import HIDDEN_LOG_CATEGORIES
from game.scene.loader import LoaderHelper, SceneLoader


CATEGORY_NAME = 'REPLAY_ANALYZER'


class ReplayOutcomeAnalysisError(RuntimeError):
    pass


class _ReplayAnalysisInput(InputDevice):

    def IsInputReady(self) -> bool:
        return False

    def IsConnect(self) -> bool:
        return True


class _ReplayAnalysisOutput(ConsoleDevice):

    def IsSyncReady(self) -> bool:
        return True


class _ReplayAnalysisDeviceManager(DeviceManager):

    def __init__(self) -> None:
        super().__init__()
        self.failure_reason = ''

    def CreateDevices(self, controller: Any):
        return (
            _ReplayAnalysisOutput(controller, self),
            _ReplayAnalysisInput(controller, self),
        )

    def DoGetInput(
        self,
        data: AskOptionPayload,
        player_id: int,
        check: Any,
    ) -> str|None:
        # Raising here would be caught by Message.Send as a game crash. End the
        # isolated analysis game cleanly and raise from Analyze() afterwards.
        from engine import Engine
        game = Engine.game
        if data.replay_input:
            step = game.controller_manager.replay.current_step_id
            self.failure_reason = (
                f'Replay diverged at recorded input {step}; the saved choice '
                'was no longer valid.'
            )
        else:
            self.failure_reason = (
                'Replay inputs ended before the game reached a final outcome.'
            )
        if game.world and not game.world.is_game_over:
            game.world.game_over.SetExit()
        return None

    def DoWaitSync(self, player_id: int, check: Any):
        # Headless analysis never waits for rendering or browser animation.
        return None


@dataclass(frozen=True)
class ReplayOutcome:
    result: str
    game_over_reason: str
    rounds: int
    remaining_hit_points: int|None
    minions_in_play: int|None
    side_schemes_in_play: int|None

    def AsRecord(self) -> Dict[str, Any]:
        return {
            'result': self.result,
            'game_over_reason': self.game_over_reason,
            'rounds': self.rounds,
            'remaining_hit_points': self.remaining_hit_points,
            'minions_in_play': self.minions_in_play,
            'side_schemes_in_play': self.side_schemes_in_play,
        }


class ReplayOutcomeAnalyzer:

    def __init__(self, statistics: Any) -> None:
        self.statistics = statistics

    @staticmethod
    def _restore_engine_attribute(engine: Any, name: str, previous: Any) -> None:
        if previous is _MISSING:
            delattr(engine, name)
        else:
            setattr(engine, name, previous)

    def Analyze(self, file_path: str) -> ReplayOutcome:
        from engine import Engine
        from game.game import Game
        from game.test import Test

        # SceneLoader uses repository-relative paths internally. Normalize an
        # absolute replay-folder path (common in tests and deployments) before
        # handing it to the loader.
        replay_case = os.path.relpath(os.path.abspath(file_path), os.getcwd())
        scene = SceneLoader.Load(replay_case)
        if not scene:
            raise ReplayOutcomeAnalysisError('Replay could not be loaded.')
        LoaderHelper.EnsureSupportedReplay(scene)

        previous_game = getattr(Engine, 'game', _MISSING)
        previous_device_manager = getattr(Engine, 'device_manager', _MISSING)
        previous_release = Build.release
        previous_suppress_crash_save = Engine.suppress_crash_save
        previous_is_in_test = Test.is_in_test
        previous_silent_progress = Test.silent_progress
        previous_test_cases = Test.test_cases
        previous_hidden_log_categories = HIDDEN_LOG_CATEGORIES.value[:]

        device_manager = _ReplayAnalysisDeviceManager()
        analysis_game = Game(self.statistics, device_manager, None)

        try:
            Engine.device_manager = device_manager
            Engine.game = analysis_game
            Build.release = False
            Engine.suppress_crash_save = True
            Test.is_in_test = True
            Test.silent_progress = True
            Test.test_cases = []
            if 'REPLAY' not in HIDDEN_LOG_CATEGORIES.value:
                HIDDEN_LOG_CATEGORIES.value.append('REPLAY')

            scene.HackTestRule()
            analysis_game.session.SetScene(scene, 'InTesting')
            analysis_game.GameSetup()
            analysis_game.GameLoop()

            if device_manager.failure_reason:
                raise ReplayOutcomeAnalysisError(device_manager.failure_reason)

            world = analysis_game.world
            if not world or not world.game_over.is_game_over:
                raise ReplayOutcomeAnalysisError(
                    'Replay finished without reaching game over.'
                )
            if world.game_over.is_game_exit_or_undo:
                raise ReplayOutcomeAnalysisError(
                    f'Replay ended with {world.game_over.reason}, not a game outcome.'
                )

            consumed_inputs = len(
                analysis_game.controller_manager.replay.history_inputs
            )
            total_inputs = len(scene.inputs)
            if consumed_inputs != total_inputs:
                raise ReplayOutcomeAnalysisError(
                    f'Replay diverged: consumed {consumed_inputs} of '
                    f'{total_inputs} recorded inputs.'
                )
            if Log.HasError(error=True):
                raise ReplayOutcomeAnalysisError(
                    'The engine reported an error while replaying the game.'
                )

            player = world.const_players[0] if len(world.const_players) == 1 else None
            remaining_hit_points = (
                max(0, int(player.GetIdentity().health)) if player else None
            )
            minions_in_play = len(player.GetEngagedMinions()) if player else None
            side_schemes_in_play = (
                world.area_schemes_side.GetSize() if player else None
            )
            return ReplayOutcome(
                result='win' if world.game_over.players_won else 'loss',
                game_over_reason=str(world.game_over.reason or ''),
                rounds=int(world.round_id),
                remaining_hit_points=remaining_hit_points,
                minions_in_play=minions_in_play,
                side_schemes_in_play=side_schemes_in_play,
            )
        finally:
            try:
                analysis_game.Shutdown()
            finally:
                Test.is_in_test = previous_is_in_test
                Test.silent_progress = previous_silent_progress
                Test.test_cases = previous_test_cases
                HIDDEN_LOG_CATEGORIES.value = previous_hidden_log_categories
                Build.release = previous_release
                Engine.suppress_crash_save = previous_suppress_crash_save
                self._restore_engine_attribute(
                    Engine,
                    'game',
                    previous_game,
                )
                self._restore_engine_attribute(
                    Engine,
                    'device_manager',
                    previous_device_manager,
                )


_MISSING = object()
