import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401

from game.cheat.cheat import Cheat, QUICK_SAVE_FOLDER
from game.game_run.game_session import GameSession
from game.test import Test


class PersistentSavePathTests(unittest.TestCase):

    def setUp(self):
        self.original_quick_save_folder = QUICK_SAVE_FOLDER.value

    def tearDown(self):
        QUICK_SAVE_FOLDER.value = self.original_quick_save_folder

    def test_numbered_save_uses_configured_folder_and_preserves_step(self):
        QUICK_SAVE_FOLDER.value = "./runtime"

        self.assertEqual(
            Cheat.ResolveQuickSavePath("save_0.json"),
            "./runtime/save_0.json",
        )
        self.assertEqual(
            Cheat.ResolveQuickSavePath("save_3.json:-1"),
            "./runtime/save_3.json:-1",
        )

    def test_other_save_paths_are_not_rewritten(self):
        QUICK_SAVE_FOLDER.value = "./runtime"

        self.assertEqual(
            Cheat.ResolveQuickSavePath("crash.json"),
            "crash.json",
        )
        self.assertEqual(
            Cheat.ResolveQuickSavePath("custom/save_0.json"),
            "custom/save_0.json",
        )

    def test_qsave_command_writes_to_configured_folder(self):
        QUICK_SAVE_FOLDER.value = "./runtime"
        game = SimpleNamespace(
            scene=SimpleNamespace(GetSaveFileName=lambda: "unused"),
            session=SimpleNamespace(
                SaveScene=Mock(return_value="./runtime/save_0.json"),
            ),
        )
        statistics = SimpleNamespace(Save=Mock())

        with patch.object(Engine, "game", game, create=True), \
            patch.object(Engine, "statistics", statistics, create=True), \
            patch("game.cheat.cheat.Notify.Command"):
            self.assertTrue(Cheat.PreDebugExec("/save save_0.json", None))

        game.session.SaveScene.assert_called_once_with(
            name="./runtime/save_0.json",
            ex_save_name=None,
            delete_old=False,
        )

    def test_qload_command_reads_from_configured_folder(self):
        QUICK_SAVE_FOLDER.value = "./runtime"
        game = SimpleNamespace(
            session=SimpleNamespace(Load=Mock()),
        )

        with patch.object(Engine, "game", game, create=True), \
            patch("game.cheat.cheat.Notify.Command"):
            self.assertTrue(Cheat.PreDebugExec("/load save_0.json:-1", None))

        game.session.Load.assert_called_once_with(
            "./runtime/save_0.json:-1",
            None,
            "Load",
        )

    def test_save_scene_creates_configured_parent_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "runtime" / "save_0.json"
            scene = Mock()
            scene.Save.return_value = True
            session = GameSession.__new__(GameSession)
            session.scene = scene
            session.game = SimpleNamespace()

            with patch.object(Test, "IsInTesting", return_value=True):
                saved = session.SaveScene(
                    name=str(file_path),
                    delete_old=False,
                )

            self.assertEqual(saved, str(file_path))
            self.assertTrue(file_path.parent.is_dir())
            scene.Save.assert_called_once_with(
                str(file_path),
                session.game,
                playtime=None,
            )


if __name__ == "__main__":
    unittest.main()
