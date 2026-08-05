"""Run one replay through the real engine without starting the web server."""

from __future__ import annotations

import sys
import os
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m unit_test.wonder_man_replay REPLAY.json")
        return 2

    replay_path = Path(sys.argv[1]).resolve()
    if not replay_path.is_file():
        print(f"replay not found: {replay_path}")
        return 2

    # ConfigVariables reads sys.argv during Engine.Initialize().  The `test`
    # group selects the key/debug device, disables statistics, and therefore
    # does not bind the web-server port.
    sys.argv = [sys.argv[0], "-test"]

    from build import Build

    Build.release = False

    from engine import Engine
    from game.test import Test
    from game.test.test_run import TestRun

    initialized = Engine.Initialize()
    if not initialized:
        print("engine initialization failed")
        return 1

    try:
        Test.is_in_test = True
        # FileManager treats paths as repository-relative and prefixes `./`.
        replay_case = os.path.relpath(replay_path, Path.cwd())
        success = TestRun.Run(Engine.game, [replay_case])
        return 0 if success else 1
    finally:
        Test.Exit()
        Engine.Shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
