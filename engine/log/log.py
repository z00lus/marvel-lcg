import os
from core.lib import Time
from core import *
from colorama import Fore, Style

from build import Build
from engine.config import ConfigVariables

CATEGORY_NAME = "LOG"

SHOW_SILENT_LOG_CATEGORIES  = ConfigVariables.ListStr('show_silent_log_categories', [])
HIDDEN_LOG_CATEGORIES       = ConfigVariables.ListStr('hidden_log_categories', [])
CRASH_FILE                  = ConfigVariables.File('crash_file', "crash.log")
DISPLAY_SOUND_NAME          = ConfigVariables.Bool('display_sound_name', False)

def PrintUtf8(log_text: str) -> None:
    try:
        print(log_text, end="")
    except Exception as e:
        print(f"Error printing log: {e}")

class LogHelper:

    CATEGORY_COLOR: Dict['Log.CATEGORY', str] = {
        "WEB"       : f"{Fore.LIGHTMAGENTA_EX}",
        "EFFECT"    : f"{Fore.GREEN}",
        "CHEAT"     : f"{Fore.CYAN}",
        "VERSION"   : f"{Fore.BLUE}",
        "STATISTICS": f"{Fore.BLUE}",
        "ENGINE"    : f"{Fore.LIGHTBLUE_EX}",
    }

    LEVEL_COLORS: Dict['Log.LEVELS', str] = {
        'Info'      : f"{Fore.GREEN}",
        'Error'     : f"{Fore.RED}",
        'Debug'     : f"{Fore.LIGHTBLACK_EX}",
        'DebugInfo' : f"{Fore.LIGHTBLACK_EX}",
        'Warn'      : f"{Fore.YELLOW}",
        'Failed'    : f"{Style.BRIGHT}{Fore.RED}",
        'Hack'      : f"{Fore.LIGHTBLUE_EX}",
    }

    LEVELS_FOR_STATISTICS: List['Log.LEVELS'] = ['Warn', 'Error', 'Failed']

    @staticmethod
    def StatLog(category: 'Log.CATEGORY', level: 'Log.LEVELS', text: str):
        if Build.release:
            return
        def save(c: 'Log.CATEGORY'):
            if c not in Log.log_statistics:
                Log.log_statistics[c] = {}
            if level not in Log.log_statistics[c]:
                Log.log_statistics[c][level] = {}
            if text not in Log.log_statistics[c][level]:
                Log.log_statistics[c][level][text] = 0
            Log.log_statistics[c][level][text] += 1
        save(category)
        save("ALL")


    @staticmethod
    def Print(log_text: str, end: str="") -> None:
        log_text = log_text + end
        Log.all_log_text += log_text
        PrintUtf8(log_text)

    @staticmethod
    def PrintInternal(category: 'Log.CATEGORY', level: 'Log.LEVELS', infos: str) -> None:
        color_level = LogHelper.LEVEL_COLORS[level]
        color_category = LogHelper.CATEGORY_COLOR[category] if category in LogHelper.CATEGORY_COLOR else color_level
        infos = infos.replace(Fore.RESET, color_level)

        log_text = ""

        color_time = f"{Fore.LIGHTBLACK_EX}"
        time = f"{Log.GetGameTime():.3f}"

        for info_line in infos.splitlines():
            category_name = f"{category[0:3]}"
            level_name = str(level).upper()
            if category != "TEST":
                Log.all_log_text += f'[{category_name}] {time} <{level_name}> {info_line}\n'

            if Build.release:
                log_text += f'{color_level}<{level_name[0:1]}> {info_line}{Style.RESET_ALL}\n'
            else:
                log_text += f'{color_category}[{category_name}] {color_time}{time} | {color_level}{info_line}{Style.RESET_ALL}\n'

        PrintUtf8(log_text)

    @staticmethod
    def PrintLog(category: 'Log.CATEGORY', level: 'Log.LEVELS', *info: object) -> None:
        # Hide debug info in release version
        if category in HIDDEN_LOG_CATEGORIES.value:
            return

        if Build.release:
            show_caller = False
        elif level in ['Hack'] + LogHelper.LEVELS_FOR_STATISTICS:
            show_caller = True
        else:
            show_caller = False

        line = ""
        if show_caller:
            line = GetCallStack(3)

        if level in LogHelper.LEVELS_FOR_STATISTICS:
            LogHelper.StatLog(category, level, line)

        infos = " ".join(str(x) for x in info)
        if line:
            infos = line + "\n" + infos

        LogHelper.PrintInternal(category, level, infos)

class Log:

    CATEGORY = Literal["UPLOAD", "GAME", "WEB", "ENGINE", "STATISTICS", "SCENE", "TEST", "CHEAT", "EDITOR", "CONTROLLER", "CACHE", "EFFECT", "SELECTOR", "REPLAY", "PLAYER", "SENDER", "RENDER", "VERSION", "THREADS", "LOG", "NOTIFY", "LOAD", "DEVICE_MANAGER", "WEB_DEVICE_MANAGER", "JSON", "CONTROLLER_MANAGER", "TASK", "COMMAND", "PUZZLE", "ALL", "SERVER_CONFIG", "SYNC", "NEW", "RANDOM", "CHECK_NEW_VERSION", "UNIT_TEST", "FILE", "CONSOLE", "JOB", "GAME_STATE", "SKIP", "SESSION", "FAST_UNDO", "MESSAGE", "UNDO_HANDLE"]

    LEVELS = Literal['Warn', 'Error', 'Info', 'Debug', 'DebugInfo', 'Failed', 'Hack']

    log_statistics: Dict[CATEGORY, Dict[LEVELS, Dict[str, int]]] = {}

    all_log_text: str = ""
    start_time: float = 0

    ################################################################################
    #
    @staticmethod
    def Print(*info: object, end: str="\n") -> None:
        infos = " ".join(str(x) for x in info)
        LogHelper.Print(infos, end=end)

    ################################################################################
    #
    @staticmethod
    def Info(category: 'Log.CATEGORY', *info: object) -> None:
        LogHelper.PrintLog(category, 'Info', *info)

    @staticmethod
    def PrintGameInfo(*info: object, sound_name: str, render_id: int|None=None, code_info: str="") -> None:
        from core.utility.func import ROOT_DIR
        infos = " ".join(str(x) for x in info)
        info_lines: List[str] = []
        for info_line in infos.splitlines():
            info_lines.append(f"> {info_line}")
        if sound_name and DISPLAY_SOUND_NAME.value:
            info_lines[-1] += f"  ({Fore.BLACK}{sound_name}{Fore.RESET})"
        if render_id != None:
            info_lines[0] = f"> {render_id:3}: {info_lines[0][2:]}"
        if code_info:
            code_info = os.path.relpath(code_info, ROOT_DIR)
            info_lines[-1] = f"{info_lines[-1]}  {Fore.LIGHTBLACK_EX}{code_info}{Fore.RESET}"
        LogHelper.Print("\n".join(info_lines) + "\n", end="")

    @staticmethod
    def PrintNull(category: 'Log.CATEGORY', *info: object) -> None:
        pass

    @staticmethod
    def Hack(category: 'Log.CATEGORY', *info: object) -> None:
        LogHelper.PrintLog(category, 'Hack', *info)

    @staticmethod
    def Debug(category: 'Log.CATEGORY', *info: object):
        LogHelper.PrintLog(category, 'Debug', *info)

    @staticmethod
    def DebugInfo(category: 'Log.CATEGORY', *info: object):
        LogHelper.PrintLog(category, 'DebugInfo', *info)

    @staticmethod
    def DebugSilent(category: Literal["SYNC", "DEVICE_MANAGER", "WEB_DEVICE_MANAGER", "LOG", "NEW", "RANDOM", "JOB", "GAME_STATE", "SKIP", "FAST_UNDO", "MESSAGE", "UNDO_HANDLE"], *info: object):
        if category in SHOW_SILENT_LOG_CATEGORIES.value:
            LogHelper.PrintLog(category, 'Debug', *info)
        pass

    if Build.release:
        Hack        = PrintNull
        Debug       = PrintNull
        # DebugInfo   = PrintNull
        DebugSilent = PrintNull

    # No recorded in the `Log.all_log_text`
    @staticmethod
    def Test(*info: object):
        from game.test import Test
        if Test.IsInTesting() and not Test.silent_progress:
            infos = " ".join(str(x) for x in info)
            PrintUtf8(infos)

    @staticmethod
    def Warn(category: 'Log.CATEGORY', *info: object):
        LogHelper.PrintLog(category, 'Warn', *info)

    @staticmethod
    # Error
    def Assert(category: 'Log.CATEGORY', *info: object):
        LogHelper.PrintLog(category, 'Error', *info)

    @staticmethod
    def FailedTrace(category: 'Log.CATEGORY', exc: Exception, *, no_take_as_error: bool=False) -> str:
        import traceback
        info = traceback.format_exc()
        if no_take_as_error:
            LogHelper.PrintLog(category, 'Debug', info)
        else:
            LogHelper.PrintLog(category, 'Failed', info)
        return info

    @staticmethod
    def OnCrash(category: 'Log.CATEGORY', exc: Exception, name: str, function: Callable[..., Any]|None,
                # *,
                # no_take_as_error: bool=False,
                # no_save_crash: bool=False,
                ) -> str:
        from engine import Engine

        if function:
            function_name = GetFuncName(function)
        else:
            function_name = ""

        info = Log.FailedTrace(category, exc)
        Log.Debug(category, name, function_name)
        # Log.Notify(CATEGORY_NAME, "Error", function_name)

        if str(exc) == 'maximum recursion depth exceeded in comparison':
            exit()

        Engine.SaveCrash()

        if not Build.release:
            raise
        else:
            return info

    ################################################################################
    #
    @staticmethod
    def SaveCrashLog():
        from engine.file import FileManager

        file_name = CRASH_FILE.value
        Log.Info(CATEGORY_NAME, f"Save {file_name}")
        with FileManager.OpenFile(file_name, write=True) as file:
            file.Write(Log.all_log_text)

    ################################################################################
    #
    @staticmethod
    def ReportStats() -> None:
        # Log.Print('\n--- Stats ---')
        Log.Print('\nLog statistics:')

        for category in Log.log_statistics:
            if category == "ALL":
                continue
            for level in LogHelper.LEVELS_FOR_STATISTICS:
                if level not in Log.log_statistics[category]:
                    continue
                for text in Log.log_statistics[category][level]:
                    count = Log.log_statistics[category][level][text]
                    path = (text + " ").ljust(60, "-")
                    # Log.Print(f'{path} {count}', level)
                    LogHelper.PrintInternal(category, level, f'{path} {count}')
        # Log.Print('--- ----- ---')

    @staticmethod
    def Setup():
        Log.log_statistics = {}
        # Log.all_log_text = ""

    @staticmethod
    def ResetTime():
        Log.start_time = Time.GetTime()
        Log.DebugSilent(CATEGORY_NAME, "Time reset")

    @staticmethod
    def GetGameTime() -> float:
        if Log.start_time == 0:
            return 0
        return Time.GetTime() - Log.start_time

    @staticmethod
    def HasError(category: 'Log.CATEGORY|None'=None, warn: bool=False, error: bool=False) -> bool:
        if category == None:
            category = "ALL"
        if category not in Log.log_statistics:
            return False

        def check_has_key(level: 'Log.LEVELS'):
            if level not in Log.log_statistics[category]:
                return False
            return len(Log.log_statistics[category][level]) > 0

        if error:
            if check_has_key('Error'):
                return True
            if check_has_key('Failed'):
                return True
        if warn:
            if check_has_key('Warn'):
                return True
        return False
