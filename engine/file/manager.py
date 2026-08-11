from core import *
import os
from engine.config import ConfigVariables
from engine.file.file import File

CATEGORY_NAME = "FILE"

REPLAY_FOLDERS          = ConfigVariables.Folders('replay_folders', ["./replays/"])
LOAD_FOLDERS            = ConfigVariables.Folders('load_folders', ["./replays/"])
DECK_FOLDERS            = ConfigVariables.Folders('deck_folders', ["./deck/"])
STARTER_DECK_FOLDER     = ConfigVariables.Folder('starter_deck_folder', "./deck/starter")
USER_DECK_FOLDER        = ConfigVariables.Folder('user_deck_folder', "./deck/user-decks")
CAMPAIGN_DECK_FOLDER    = ConfigVariables.Folder('campaign_deck_folder', "./deck/campaign-decks")
ENCOUNTER_SETS_FOLDERS  = ConfigVariables.Folders('encounter_sets_folders', ["./data/encounter_sets/", "./data/nemesis/", "./data/"])
SCENARIOS_FOLDERS       = ConfigVariables.Folders('scenarios_folders', ["./data/scenarios/", "./data/challenges/",  "./data/"])
CUSTOM_SCENARIOS_FOLDER = ConfigVariables.Folder('custom_scenario_folder', "./data/scenarios_custom/")
DATA_FOLDER             = ConfigVariables.Folder('data_folder', "./data/")
PUZZLE_FOLDER           = ConfigVariables.Folder('puzzle_folder', "./puzzle/")
PUZZLE_TEST_FOLDER      = ConfigVariables.Folder('puzzle_test_folder', "./puzzle/test/")

class FileManager:

    @staticmethod
    def OpenFile(file_name: str, *, read: bool=False, write: bool=False, bin: bool=False) -> File:
        return File(file_name, read=read, write=write, bin=bin)

    ################################################################################
    #
    @staticmethod
    def JoinPath(file_path: str, file_name: str) -> str:
        return os.path.join(file_path, file_name)

    @staticmethod
    def ReplacePath(file_path: str, replace: str) -> str:
        return os.path.relpath(file_path, replace)

    @staticmethod
    def IsFile(file_path: str) -> bool:
        return os.path.isfile(file_path)

    @staticmethod
    def IsDir(file_path: str) -> bool:
        return os.path.isdir(file_path)

    @staticmethod
    def MakeDir(file_path: str) -> bool:
        if file_path:
            os.makedirs(file_path, exist_ok=True)
        return True

    @staticmethod
    def ListDir(file_path: str) -> List[str]:
        return os.listdir(file_path)

    @staticmethod
    def ListFiles(*folders: str, ext: str|None=None, check_file_name: Callable[[str], bool]|None=None) -> List[str]:
        def do_list(folder: str) -> List[str]:
            if FileManager.Exists(folder):
                return [FileManager.JoinPath(folder, f) for f in FileManager.ListDir(folder) if \
                    FileManager.IsFile(FileManager.JoinPath(folder, f)) and \
                    ext == None or ext == FileManager.GetExtension(f) and \
                        (
                            check_file_name == None or \
                            check_file_name(f)
                        )
                    ]
            else:
                return []
        files: List[str] = []
        for folder in folders:
            files += do_list(folder)
        return files

    @staticmethod
    def Rename(file_path: str, new_path: str):
        os.rename(file_path, new_path)
        return True

    @staticmethod
    def Replace(file_path: str, new_path: str):
        os.replace(file_path, new_path)
        return True

    @staticmethod
    def GetBaseName(file_path: str):
        return os.path.basename(file_path)

    @staticmethod
    # "a.json" -> ".json"
    def GetExtension(file_path: str) -> str:
        return os.path.splitext(file_path)[1]

    @staticmethod
    def MoveFile(file_path: str, target_directory: str) -> bool:
        """
        Move specified files to the target directory if they do not already exist there.
        """
        # Ensure the target directory exists
        FileManager.MakeDir(target_directory)

        # Extract the filename from the source path
        filename = FileManager.GetBaseName(file_path)
        target_path = FileManager.JoinPath(target_directory, filename)

        # Check if the file already exists in the target directory
        if not FileManager.Exists(target_path):
            try:
                # shutil.move(file_path, target_path)
                FileManager.Rename(file_path, target_path)
                return True
            except Exception:
                return False
        else:
            return False

    @staticmethod
    def Delete(file_path: str):
        os.remove(file_path)
        return True

    @staticmethod
    def GetDirName(file_path: str) -> str:
        return os.path.dirname(file_path)

    @staticmethod
    def Exists(file_path: str) -> bool:
        return os.path.exists(file_path)

    @staticmethod
    def IsSameFile(file1: str, file2: str) -> bool:
        # Get the absolute paths
        abs_file1 = os.path.abspath(file1)
        abs_file2 = os.path.abspath(file2)
        
        # Compare the absolute paths
        return abs_file1 == abs_file2

    @staticmethod
    def SanitizeFilename(filename: str) -> str:
        import re
        # Define a regex pattern for invalid characters in a filename
        # This pattern includes characters that are generally not allowed in filenames
        invalid_pattern = r'[<>:"/\\|?*]'

        # Replace invalid characters with an empty string
        sanitized = re.sub(invalid_pattern, '', filename)

        sanitized = sanitized.replace(' ', '_').replace('.', '')

        sanitized = re.sub(r'_+', '_', sanitized)

        return sanitized

    @staticmethod
    def EditCode(file_path: str) -> None:
        System.Run(f'code {file_path}')

    @staticmethod
    def CleanName(name: str) -> str:
        return name.lstrip('*').strip().lower().replace(" - ", "_").replace(" & ", "_").replace(' ', '_').replace("'", "").replace("-", "_").replace("!", "").replace("?", "").replace("(", "").replace(")", "").replace(".", "").replace(",", "").replace("\"", "").replace("&", "_").replace("#", "").replace("/", "")

    @staticmethod
    def IsDrivePath(file_name: str) -> bool:
        # Check if the file name starts with a drive letter followed by a colon and a backslash or forward slash
        if len(file_name) >= 3 and file_name[1:3] == ':\\':
            return file_name[0].isalpha()
        elif len(file_name) >= 3 and file_name[1:3] == ':/':
            return file_name[0].isalpha()
        return False

    @staticmethod
    def FormatPath(path: str) -> str:
        normalized_path = os.path.normpath(path)
        if normalized_path[1] == ":":
            pass
        elif not normalized_path.startswith('.'):
            # Ensure the path starts with './'
            normalized_path = './' + normalized_path
        return normalized_path

    JsonType = Literal['Config','Hero','EncounterSet','Replay','Campaign', 'SetInfo', 'Puzzle']

    @staticmethod
    def FindJsonPath(load_type: 'JsonType', *file_names: str, nullable: bool=False) -> str|None:
        from engine.log import Log

        def get_type_path_list() -> List[str]:
            if load_type == 'Config':
                return ['./']
            if load_type == 'Replay':
                return ['./'] + REPLAY_FOLDERS.value + LOAD_FOLDERS.value
            if load_type == 'Hero':
                return DECK_FOLDERS.value + [CAMPAIGN_DECK_FOLDER.value, USER_DECK_FOLDER.value, STARTER_DECK_FOLDER.value]
            if load_type == 'EncounterSet':
                return ENCOUNTER_SETS_FOLDERS.value
            if load_type == 'Campaign':
                return SCENARIOS_FOLDERS.value + [CUSTOM_SCENARIOS_FOLDER.value]
            if load_type == 'SetInfo':
                return ["./", DATA_FOLDER.value]
            if load_type == 'Puzzle':
                return ["./", PUZZLE_FOLDER.value]

        path_list = get_type_path_list()

        for file_name in file_names:
            if FileManager.IsDrivePath(file_name):
                return file_name
            if not file_name.endswith(".json"):
                file_name += ".json"
            for folder in ['./'] + path_list:
                file_path = FileManager.JoinPath(folder, file_name)
                if FileManager.Exists(file_path):
                    return FileManager.FormatPath(file_path)
        if nullable:
            Log.Warn(CATEGORY_NAME, f"File {file_names} not found")
            return None
        else:
            Log.Assert(CATEGORY_NAME, f"File {file_names} not found")
            return None
