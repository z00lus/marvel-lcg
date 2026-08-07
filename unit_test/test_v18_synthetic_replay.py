from pathlib import Path
import unittest
from unittest.mock import Mock

from engine import Engine
from engine.controller.module.replay import InputModule
from engine.lib import Json, Ver
from game.scene.loader import LoaderHelper


FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures/v18/replay_loader_minimal.json"
)


class V18SyntheticReplayTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()

    def test_fixture_checksum_and_rules_are_valid(self):
        _, checksum = Json.LoadInternal(str(FIXTURE))
        self.assertEqual(checksum, "Ok")

        scene = LoaderHelper.Loads(str(FIXTURE))
        LoaderHelper.EnsureSupportedReplay(scene)
        self.assertEqual(scene.seed, 18001)
        self.assertEqual([item.step for item in scene.inputs], [1, 2])

    def test_serialized_input_stream_replays_from_start_to_finish(self):
        scene = LoaderHelper.Loads(str(FIXTURE))
        manager = Mock()
        replay = InputModule(manager)
        replay.SetReplayInputs(scene.inputs)

        replayed = []
        while True:
            operation, read_ok = replay.GetReplayOperation(
                is_puzzle=True,
                check_crc=False,
            )
            self.assertTrue(read_ok)
            if operation is None:
                break
            replayed.append(operation)
            replay.Push(operation)

        self.assertEqual(replayed, scene.inputs)
        self.assertEqual(replay.history_inputs, scene.inputs)
        self.assertEqual(replay.current_step_id, len(scene.inputs))
        self.assertEqual(replay.replay_step_id, len(scene.inputs))


if __name__ == "__main__":
    unittest.main()
