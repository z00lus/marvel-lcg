from core import *
from game.test import Test
from engine import Engine
from engine.log import Log, Notify
from engine.profile import Coverage, Profile
from engine.file import FileManager
from game.world import World
from engine.config import ConfigVariables

CATEGORY_NAME = "COMMAND"

QUICK_SAVE_FOLDER = ConfigVariables.Folder('quick_save_folder', ".")

class Cheat:

    @staticmethod
    def ResolveQuickSavePath(path: str) -> str:
        """Place numbered table saves in the configured persistent folder."""
        import re

        match = re.fullmatch(r"(save_[0-3]\.json)(:-?\d+)?", path)
        if not match:
            return path

        file_path = FileManager.JoinPath(
            QUICK_SAVE_FOLDER.value,
            match.group(1),
        )
        return file_path + (match.group(2) or "")

    ################################################################################
    # No save in history inputs
    @staticmethod
    def TryPreDebugExec(input_command: str, world: 'World|None') -> bool:
        try:
            return Cheat.PreDebugExec(input_command, world)
        except Exception as exc:
            info = Log.FailedTrace(CATEGORY_NAME, exc)
            if world:
                world.render.ErrorOccurred(info)
        return False

    @staticmethod
    def PreDebugExec(input_command: str, world: 'World|None') -> bool:
        import re
        game = Engine.game

        def try_skip_to(step: int):
            if step == 0: # hack
                game.session.SkipTo(game.controller_manager.replay.current_step_id)
            elif game.controller_manager.skip.skip_to >= game.controller_manager.replay.current_step_id:
                step += game.controller_manager.replay.current_step_id
                game.session.SkipTo(step)
            elif game.controller_manager.replay.current_step_id < step:
                game.session.SkipTo(step)
            else:
                step = game.controller_manager.replay.current_step_id - step
                game.session.Undo(step)

        command = Cheat.ResolveQuickSavePath(input_command)
        # Load scene
        # Start with version [0.5.7.104]
        if not command.startswith("/"):
            if FileManager.IsDrivePath(command):
                game.session.Load(command, None, "Load")
                return True
            elif command.startswith('debug') or \
                command.startswith('crash') or \
                command.startswith('save') or \
                command.startswith('./') or \
                command.startswith('.\\') or \
                command.endswith('.json') or \
                re.match(r"^\[\d+\.\d+\.\d+", command) or \
                re.match(r".*\.json\:\d+$", command):
                game.session.Load(command, None, "Load")
                return True
            elif command.isdigit():
                step = int(command)
                try_skip_to(step)
                return True
            elif command[0] == '-' and command[1:].isdigit():
                step = int(command[1:])
                game.session.Undo(step)
                return True

        ################################################################################
        #
        # /T 23             Test start from 23
        # /T 117:12         Test case 117, goto step 12
        # /T make_the_call  Test specific category
        def do_test(args: str=""):
            if args != "" and ":" in args:
                load_id = 0
                category = None
                skip_to = 0
                splited_data = args.split(":")
                if len(splited_data) == 2:
                    # /T 54:20
                    # /T restricted:20
                    if splited_data[0].isdigit():
                        load_id = int(splited_data[0])
                    else:
                        category = splited_data[0]
                    if splited_data[1].isdigit():
                        skip_to = int(splited_data[1])
                elif len(splited_data) == 3:
                    # /T restricted:0:20
                    category = splited_data[0]
                    if splited_data[1].isdigit():
                        load_id = int(splited_data[1])
                    if splited_data[2].isdigit():
                        skip_to = int(splited_data[2])

                case_name = Test.GetTestCases(category)[load_id]
                game.session.Load(case_name, skip_to, "Load")
            else:
                test_category = ""
                start_index = 0

                if args == "":
                    pass
                elif args.isdigit() and len(args) < 5:
                    start_index = int(args)
                else:
                    test_category = args

                if world:
                    world.game_over.SetExit()
                # Exit current scene
                game.session.ExitWait()
                test_category = test_category.replace("?", "")
                Test.SetStart(start_index, test_category)

                game.controller_manager.replay.Clear()
                game.state.SetStartState("InTesting")

        def do_save(args: str=""):
            name = game.scene.GetSaveFileName()
            if args:
                name = Cheat.ResolveQuickSavePath(args)
                ex_save_name = None
            else:
                name = None
                ex_save_name = f'./save.json'
            Engine.statistics.Save()
            if game.session.SaveScene(name=name, ex_save_name=ex_save_name, delete_old=False):
                return f"Save: {name}"

        def do_load(args: str):
            game.session.Load(
                Cheat.ResolveQuickSavePath(args),
                None,
                "Load",
            )

        # def do_save_level(args: List[str]):
        #     name = game.scene.scene.save_name
        #     game.scene.SaveLevel(f'./level_{name}.json', world)
        #     Log.Notify(CATEGORY_NAME, "", f"Save: {name}")

        # def do_load_level(args: List[str]):
        #     # name = " ".join(args)
        #     # game.LoadLevel(name)
        #     pass

        def do_restart(args: str|None=None):
            if args != None:
                seed = int(args)
            else:
                seed = None
            game.Restart(seed)

        def do_comment(*args: str):
            game.scene.SetMetadataStr("comment", " ".join(args))
            return f"Comment Update: {game.scene.comment}"

        def do_comment_by(args: str="0"):
            index = int(args)
            return do_comment(game.scene.campaign.encounter_sets[index])

        def do_undo(args: str|Literal["auto"]="1"):
            if args:
                current_step_id = game.controller_manager.replay.current_step_id
                undo_count = game.scene.step + [f"{current_step_id}_{args}"]
                game.scene.SetMetadataList('step', undo_count)

            step = 1
            if args == "auto":
                last_step = game.controller_manager.undo.last_step
                if last_step != 0:
                    try_skip_to(last_step)
                    return
            else:
                step = int(args)
            game.session.Undo(step)

        def do_goto(args: Literal["turn_begin", "end"]|str):
            if args:
                current_step_id = game.controller_manager.replay.current_step_id
                goto_count = game.scene.step + [f"{current_step_id}_{args}"]
                game.scene.SetMetadataList('step', goto_count)

            if args == 'turn_begin':
                try_skip_to(game.controller_manager.last_turn_start_step_id)
            elif args == 'end':
                step = len(game.controller_manager.replay.replay_inputs)
                game.session.SkipTo(step)
            elif args.isdigit():
                step = int(args)
                try_skip_to(step)

        def do_replay_goto(args: str):
            target_step = int(args)
            game.session.ReplayGoto(target_step)

        def do_step(args: str):
            step = int(args)
            if game.controller_manager.skip.skip_to >= game.controller_manager.replay.current_step_id:
                step += game.controller_manager.replay.current_step_id
            game.session.StepTo(step)

        def do_skip(args: str):
            if args == "round":
                game.session.SkipTo("Round")
            elif args == "turn":
                game.session.SkipTo("Turn")
            elif args == "phase":
                game.session.SkipTo("Phase")
            else:
                step = int(args)
                try_skip_to(step)

        def do_update_replay(args: str):
            step = int(args)
            game.controller_manager.replay.UpdateReplayStepId(step)

        def do_coverage_report(args: str):
            text = ''
            if args == '':
                text = Coverage.Report()
            elif args == 'all':
                text = Coverage.Report("All")
            elif args == 'uncall':
                text = Coverage.Report("Uncall")
            return text

        def do_profile(name: str="Game", command: str="print"):
            ENABLE_PROFILE_CATEGORY = ConfigVariables.ListStr('enable_profile_category')

            if name in ENABLE_PROFILE_CATEGORY.value:
                profiler = Profile.Get(name)
                text = ""
                if command == "print":
                    text = profiler.Print()
                elif command == "start" or command == "enable":
                    profiler.Start()
                elif command == "end" or command == "disable":
                    profiler.End()
                Log.Print(text)

            Log.Print(Tracker.PrintStats())

            assert world
            Log.Print(f"{len(world.object_manager.card_dict)=}")
            Log.Print(f"{len(world.object_manager.effect_dict)=}")
            Log.Print(f"{len(world.object_manager.paying_effect_dict)=}")
            Log.Print(f"{len(world.object_manager.message_dict)=}")
            return ""

        ################################################################################
        #
        actions: Dict[str, Callable[[Any], str|None]] = {
            "/test":            do_test,
            "/T":               do_test,
            "/save":            do_save,
            "/load":            do_load,
            # "/save_level":      do_save_level,
            # "/load_level":      do_load_level,
            "/restart":         do_restart,
            "/comment":         do_comment,
            "/C":               do_comment,
            "/cs":              do_comment_by,
            "/undo":            do_undo,
            '/goto':            do_goto,
            '/replay_goto':     do_replay_goto,
            '/step':            do_step, # 't'
            '/skip':            do_skip, # 's'
            '/replay':          do_update_replay,
            '/R':               do_update_replay,
            '/call_log':        do_coverage_report,
            '/CL':              do_coverage_report,
            '/P':               do_profile,
        }
            # Log.Debug(input_command)

        if command.startswith("/"):
            parts = command.split()
            command = parts[0]
            args = parts[1:]
        else:
            return False

        if command in actions:
            Log.Debug(CATEGORY_NAME, input_command)
            try:
                text = actions[command](*args)
                if text == "":
                    text = command
                if text != None:
                    Notify.Command(text)
            except Exception as exc:
                Log.Print(f"Error when running debug command: {command}")
                Log.FailedTrace(CATEGORY_NAME, exc, no_take_as_error=True)
            return True

        return False
