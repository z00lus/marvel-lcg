import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from game.game import ACTIVE_SESSION_FILE, Game


class ActiveSessionTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_active_session_file = ACTIVE_SESSION_FILE.value
        ACTIVE_SESSION_FILE.value = str(Path(self.temp_dir.name) / 'save_active_session.json')

    def tearDown(self):
        ACTIVE_SESSION_FILE.value = self.original_active_session_file
        self.temp_dir.cleanup()

    def make_game(self, *, running=True, game_over=False):
        game = Game.__new__(Game)
        world = SimpleNamespace(is_game_over=game_over)
        scene = SimpleNamespace(is_puzzle=False)
        session = SimpleNamespace(
            world=world,
            scene=scene,
            SaveScene=Mock(),
            Load=Mock(),
            NewGame=Mock(),
        )
        replay = SimpleNamespace(is_replay=False, SetIsReplay=Mock())
        game.state = SimpleNamespace(is_running=running)
        game.session = session
        game.controller_manager = SimpleNamespace(
            replay=replay,
            OnNewGame=Mock(),
        )
        game.active_session_enabled = True
        return game

    def test_new_game_replaces_the_previous_active_session(self):
        game = self.make_game(running=False)
        game.session.world = None
        Path(game.active_session_file).write_text('old session', encoding='utf-8')

        descriptor = object()
        game.NewGame(descriptor)

        self.assertFalse(Path(game.active_session_file).exists())
        self.assertTrue(game.active_session_enabled)
        game.controller_manager.replay.SetIsReplay.assert_called_once_with(False)
        game.session.NewGame.assert_called_once_with(descriptor)
        game.controller_manager.OnNewGame.assert_called_once_with()

    def test_active_session_save_atomically_replaces_the_checkpoint(self):
        game = self.make_game()
        Path(game.active_session_file).write_text('old session', encoding='utf-8')

        def save_scene(*, name, delete_old):
            self.assertEqual(name, game.active_session_temp_file)
            self.assertFalse(delete_old)
            Path(name).write_text('new session', encoding='utf-8')
            return name

        game.session.SaveScene.side_effect = save_scene

        self.assertTrue(game.SaveActiveSession())
        self.assertEqual(
            Path(game.active_session_file).read_text(encoding='utf-8'),
            'new session',
        )
        self.assertFalse(Path(game.active_session_temp_file).exists())

    def test_continue_joins_a_live_game_without_reloading_it(self):
        game = self.make_game()

        self.assertEqual(game.ContinueActiveSession(), 'live')
        game.session.Load.assert_not_called()
        game.controller_manager.OnNewGame.assert_not_called()

    def test_continue_restores_all_saved_choices_as_a_normal_game(self):
        game = self.make_game(running=False)
        Path(game.active_session_file).write_text('saved session', encoding='utf-8')

        self.assertEqual(game.ContinueActiveSession(), 'loaded')
        game.controller_manager.replay.SetIsReplay.assert_called_once_with(False)
        game.session.Load.assert_called_once_with(game.active_session_file, -1, 'Load')
        game.controller_manager.OnNewGame.assert_called_once_with()

    def test_completed_or_missing_session_is_not_available(self):
        game = self.make_game(game_over=True)

        self.assertFalse(game.HasActiveSession())
        self.assertIsNone(game.ContinueActiveSession())


if __name__ == '__main__':
    unittest.main()
