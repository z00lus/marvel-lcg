from __future__ import annotations

import importlib
from unittest import TestCase
from unittest.mock import Mock, patch

# Match the application's normal import order without starting the server.
from engine import Engine


puzzle_module = importlib.import_module("game.puzzle.puzzle")


def build_world(card_ids):
    """A world exposing just the object_manager.card_dict Exec() reads."""
    world = Mock()
    world.object_manager.card_dict = {
        card_id: Mock(face=f"face-{card_id}") for card_id in card_ids
    }
    return world


class PuzzleExecBindingTests(TestCase):

    def test_c_shorthands_are_visible_to_the_command(self):
        """`Puzzle.X(cN)` must resolve cN to that object's face.

        Regression test for a Python 3.13 failure: the bindings used to be made
        with `exec(f'c{c} = ...')` and read by a following bare `exec(command)`,
        which relied on locals() returning the same cached dict twice. PEP 667
        made locals() an independent snapshot, so the bindings vanished and this
        raised `NameError: name 'c7' is not defined` during game setup.
        """
        world = build_world([0, 7])

        with patch.object(puzzle_module, "RunPuzzle") as run_puzzle_class:
            puzzle = run_puzzle_class.return_value
            puzzle_module.PuzzleHelper.Exec(["Puzzle.Ready(c7)"], world)

        puzzle.Ready.assert_called_once_with("face-7")

    def test_every_card_id_is_bound(self):
        world = build_world([0, 3, 11])

        with patch.object(puzzle_module, "RunPuzzle") as run_puzzle_class:
            puzzle = run_puzzle_class.return_value
            puzzle_module.PuzzleHelper.Exec(
                ["Puzzle.Damage(c3, 2)", "Puzzle.Exhaust(c11)"],
                world,
            )

        puzzle.Damage.assert_called_once_with("face-3", 2)
        puzzle.Exhaust.assert_called_once_with("face-11")

    def test_non_puzzle_calls_are_still_rejected(self):
        """The AST guard must survive the namespace change."""
        world = build_world([0])

        with patch.object(puzzle_module, "RunPuzzle"):
            with self.assertRaises(ValueError):
                puzzle_module.PuzzleHelper.Exec(["print('hi')"], world)

    def test_unknown_shorthand_still_raises(self):
        """A puzzle naming a card that is not in play is a real error."""
        world = build_world([0, 1])

        with patch.object(puzzle_module, "RunPuzzle"):
            with self.assertRaises(NameError):
                puzzle_module.PuzzleHelper.Exec(["Puzzle.Ready(c99)"], world)


if __name__ == "__main__":
    import unittest
    unittest.main()
