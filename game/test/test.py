from core import *
from game import *
from engine.log import Log
from engine.file import FileManager
from engine.config import ConfigVariables

REPLAY_FOLDERS = ConfigVariables.Folders('replay_folders')

class Test:

    is_in_test = False
    silent_progress = False
    test_cases: List[str] = []

    @staticmethod
    def GetTestCases(category: str|None=None) -> List[str]:
        # We can't save the `all_cases` because it will change after we save a new scene
        all_cases: List[str] = []
        def not_start_with(f: str):
            return not f.startswith("_")
        for replays_folder in REPLAY_FOLDERS.value:
            all_cases += FileManager.ListFiles(replays_folder, ext=".json", check_file_name=not_start_with)

        def extract_version(s: str):
            import re
            match = re.search(r'\[(.*?)\]', s)
            if match:
                return tuple(map(int, match.group(1).split('.')))
            return ()

        all_cases = sorted(all_cases, key=extract_version)

        test_cases = all_cases
        if category:
            test_cases = [x for x in test_cases if category in x]
        return test_cases

    @staticmethod
    def SetStart(start_id: int, test_category: str):
        Test.test_cases = Test.GetTestCases(test_category)[start_id:]

    @staticmethod
    def Exit():
        Test.is_in_test = False
        Test.test_cases = []

    @staticmethod
    def Run(game: 'Game') -> bool:
        if not game.state.start_state.is_in_testing:
            return False

        from game.test.test_run import TestRun
        if Test.test_cases:
            Test.is_in_test = True
            success = TestRun.Run(game, Test.test_cases, do_save=True)
            exit_test = success
        else:
            success = False
            Log.Print("No cases for testing")
            game.state.SetStartState('')
            exit_test = True
        TestRun.RunEnd(game, success, exit_test)
        return True

    @staticmethod
    def IsInTesting() -> bool:
        return Test.is_in_test
