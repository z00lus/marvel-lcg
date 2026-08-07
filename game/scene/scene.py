from core import *
from core.lib import Time
from game.scene.replay import *
from engine.lib import Json, Ver
from engine.log import Log
from engine.file import FileManager
from engine.config import ConfigVariables
from game import *

CATEGORY_NAME = "SCENE"

# These rules will be added for testing file, use when change some new rules as default
TEST_RULES = ConfigVariables.ListStr('test_rules', [])

METADATA_KEY_LIST = Literal[
    "step", "clients"
]

METADATA_KEY_BOOL = Literal[
    "is_puzzle"
]

METADATA_KEY_INT = Literal[
    "seed"
]

METADATA_KEY_STR = Literal[
    "time", "path", "comment", "cover", "report", "sign"
]

METADATA_KEY_FLOAT = Literal[
    "playtime"
]

METADATA_KEY = METADATA_KEY_LIST | METADATA_KEY_BOOL | METADATA_KEY_INT | METADATA_KEY_STR | METADATA_KEY_FLOAT

@dataclass
class Scene:
    version: str = field(default_factory=lambda: "")
    metadata: Dict[METADATA_KEY, Union[str, int, bool]] = field(default_factory=lambda: {})
    rules: List[str] = field(default_factory=lambda: [])

    campaign: CampaignDescriptor = field(default_factory=lambda: CampaignDescriptor())
    players: Sequence[HeroDescriptor] = field(default_factory=lambda: [])

    puzzle: List[str] = field(default_factory=lambda: [])

    inputs: List[OperationDescriptor] = field(default_factory=lambda: [])

    def GetSaveFileName(self, use_comment: bool=True) -> str:
        return f"[{Ver.version}]-{self.GetName(use_comment)}"

    @property
    def name(self) -> str:
        return self.GetName()

    def GetName(self, use_comment: bool=True) -> str:
        from engine import Engine
        game = Engine.game

        name = ''

        if self.is_puzzle:
            name = 'puzzle-'

        if use_comment and self.comment:
            name += f"{self.comment}"
        else:
            for player in self.players:
                name += f'{player.name}-'
            name += f'{self.campaign.name}'
            if self.campaign.challenges:
                name += '-' + f'-'.join(self.campaign.challenges)
            elif self.campaign.expert:
                name += f'-expert'

            if game.world and game.world.rule.mode_campaign.val:
                name += f'-campaign'

        inputs = game.controller_manager.replay.history_inputs
        name += f'-({len(inputs)})'

        if game.session.world:
            for test_card_id in sorted(game.session.world.cheat.test_cards):
                if test_card_id not in ["01088", "01089", "01090"]:
                    name += f'-{test_card_id}'

        for input in inputs:
            if input.effect.GetDebugCommand():
                name += f'-debug'
                break

        if self.seed != 0:
            name += f'-({str(self.seed)})'

        return FileManager.SanitizeFilename(name.lower())

    def UpdateInputs(self, game: 'Game'):
        self.inputs = game.controller_manager.replay.history_inputs

    def PrepareSave(self, game: 'Game', *, playtime: float|None, report: str|None=None, clients: List[str]|None=None):
        from engine.user.user_info import UserInfo

        self.UpdateInputs(game)

        if self.sign == "":
            self.SetMetadataStr("sign", UserInfo.fingerprint)

        if self.time == "":
            self.SetMetadataStr("time", Time.Format())

        data = self
        if self.is_puzzle:
            for input in data.inputs:
                delattr(input, 'step')
                delattr(input, 'event')
                delattr(input, 'crc')

        if playtime:
            self.SetMetadataFloat("playtime", playtime)

        # Abandoned
        for key in ["undo_count", "goto_count"]:
            self.metadata.pop(key, None) # type: ignore

        if report:
            self.SetMetadataStr("report", report)
        if clients:
            self.SetMetadataList("clients", clients)

        # Sort by key
        ordered_keys = ['sign'] + [key for key in self.metadata if key not in ['sign', 'clients', 'report', 'step']] + ['report', 'clients', 'step']
        sorted_metadata: Dict[METADATA_KEY, Union[str, int, bool]] = {key: self.metadata[key] for key in ordered_keys if key in self.metadata}
        self.metadata = sorted_metadata

    def Save(self, file_path: str, game: 'Game', *, playtime: float|None=None) -> bool:
        if self.is_puzzle:
            return False

        # if self.is_puzzle:
        #     if 'path' in self.metadata:
        #         del self.metadata['path']
        #     if 'time' in self.metadata:
        #         del self.metadata['time']
        #     # if 'rule' in self.metadata:
        #     #     del self.metadata['rule']
        self.PrepareSave(game, playtime=playtime)

        path = FileManager.GetDirName(file_path)
        FileManager.MakeDir(path)
        # import copy
        # if min:
        #     data = copy.deepcopy(self)
        #     for input in data.inputs:
        #         del input.index
        #         del input.controller_id
        #         del input.event
        #         del input.effect.name
        #         del input.effect.card.name
        #         for target in input.effect.targets:
        #             del target.name
        #         for resource in input.effect.resources:
        #             del resource.name
        # else:
        #     data = self

        # Version 6
        # for input in self.inputs:
        #     del input.effect.name
        #     del input.hash

        data = self
        # DebugBreak()
        Json.Save(data, file_path, ignore_check_sum=False)
        Log.Info(CATEGORY_NAME, f"Saved: {file_path}")
        return True

    # Call follow `Json.LoadAs` 
    def UpdateVersion(self):
        if "mode_skirmish" in self.metadata: # type: ignore
            self.rules.append("mode_skirmish")
            self.metadata.pop("mode_skirmish") # type: ignore
        if "mode_heroic" in self.metadata: # type: ignore
            mode_heroic = self.metadata["mode_heroic"] # type: ignore
            self.rules.append(f"mode_heroic_{mode_heroic}")
            self.metadata.pop("mode_heroic") # type: ignore
        if "rule" in self.metadata: # type: ignore
            rule = self.metadata["rule"] # type: ignore
            if rule == "1.5":
                self.rules.append(f"rule_15")
            self.metadata.pop("rule") # type: ignore
        if not Ver(self.version).IsCreateHeroDeckFirst():
            self.rules.append("create_player_deck_first")
        if not Ver(self.version).IsDeadpoolsEncounter():
            if "crisis_of_infinite_deadpools" in self.rules:
                self.rules.remove("crisis_of_infinite_deadpools")
            else:
                self.rules.append("no_crisis_of_infinite_deadpools")
        else:
            if "crisis_of_infinite_deadpools" in self.rules:
                self.rules.remove("crisis_of_infinite_deadpools")

        if not Ver(self.version).IsFixTreachery() and \
            'fix_treachery' not in self.rules:
            self.rules.append("no_fix_treachery")

        if "encounter_cards_ignore_crisis" in self.rules:
            self.rules.remove("encounter_cards_ignore_crisis")

        if "mode_campaign" in self.rules and not self.campaign.campaign_id:
            self.campaign.InferCampaignId()

        del self.campaign.modular_sets
        self.rules = list(sorted(set(self.rules)))

    def HackTestRule(self):
        # from engine import Engine
        # if "rule_15" in self.rules:
        #     self.rules.remove("rule_15")
        # else:
        #     self.rules += TEST_RULES.value
        #     self.rules = list(set(self.rules))
        pass

    def SetMetadataList(self, key: METADATA_KEY_LIST, value: List[str]):
        str_list = Types.ListToStrList(value)
        self.metadata[key] = str_list

    def SetMetadataBool(self, key: METADATA_KEY_BOOL, value: bool):
        self.metadata[key] = value

    def SetMetadataInt(self, key: METADATA_KEY_INT, value: int):
        self.metadata[key] = value

    def SetMetadataStr(self, key: METADATA_KEY_STR, value: str):
        self.metadata[key] = value

    def SetMetadataFloat(self, key: METADATA_KEY_FLOAT, value: float):
        self.metadata[key] = f"{value:.1f}"

    def SetSeed(self, value: int):
        self.SetMetadataInt("seed", value)

    ################################################################################
    #
    def GetMetadataList(self, key: METADATA_KEY_LIST) -> List[str]:
        str_list = str(self.metadata.get(key, ""))
        return Types.StrListToList(str_list)

    def GetMetadataBool(self, key: METADATA_KEY_BOOL) -> bool:
        return bool(self.metadata.get(key, False))

    def GetMetadataInt(self, key: METADATA_KEY_INT) -> int:
        return int(self.metadata.get(key, 0))

    def GetMetadataStr(self, key: METADATA_KEY_STR) -> str:
        return str(self.metadata.get(key, ""))

    def GetMetadataFloat(self, key: METADATA_KEY_FLOAT) -> float:
        return float(self.metadata.get(key, 0))

    ################################################################################
    #
    @property
    def time(self) -> str:
        return self.GetMetadataStr("time")

    @property
    def path(self) -> str:
        return self.GetMetadataStr("path")

    @property
    def seed(self) -> int:
        return self.GetMetadataInt("seed") # -1 means random

    @property
    def comment(self) -> str:
        return self.GetMetadataStr("comment")

    @property
    def is_puzzle(self) -> bool:
        return self.GetMetadataBool("is_puzzle")

    @property
    def cover(self) -> str:
        return self.GetMetadataStr("cover")

    @property
    def playtime(self) -> float:
        return self.GetMetadataFloat("playtime")

    @property
    def step(self) -> List[str]:
        return self.GetMetadataList("step")

    @property
    def sign(self) -> str:
        return self.GetMetadataStr("sign")
