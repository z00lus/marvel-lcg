from enum import Enum
from core import *
from game.player import *
from game.effect import *

class EffectFailure(str, Enum):
    OK                      = "",
    NoProcess               = "no process",
    OutOfPlay               = "out of play",
    BindFaceIsDefeating     = "bind face is defeating",
    UpdateLegalTargets      = "update legal targets",
    NoCostTarget            = "no cost target",
    HasCostButNoAskPlayer   = "has cost but no ask player",
    TypeCountNotEnough      = "type count not enough",
    CheckTarget             = "check target",
    CheckPay                = "check pay",
    AlreadyProcessed        = "already processed in this message",
    TreatAsBlank            = "treat as blank",
    IsRemoved               = "is removed",
    MaxTargetsIsZero        = "max targets is 0",
    NoFilterTargets         = "no filter targets",
    TargetNum               = "targets num"
    DuplicateTarget         = "duplicate target"
    EngagedDifferentPlayer  = "engaged different player"
    AlreadyResolvesDefense  = "already resolves defense ability"

class FailureReason:

    def __init__(self, effect: 'Effect') -> None:
        self.effect = effect
        # Debug only, player_id (0 means scenario), reasons
        self.reasons: Dict[int, List[str]] = {
            -1: [EffectFailure.NoProcess],
             0: [EffectFailure.NoProcess],
             1: [EffectFailure.NoProcess],
             2: [EffectFailure.NoProcess],
             3: [EffectFailure.NoProcess]
        }

    def SetText(self, player: 'Player|None|User', text: str):
        if self.effect.ability.flags.is_statistics:
            return

        from game.player import Player
        if player == None:
            player_id = -1
        elif isinstance(player, Player):
            player_id = player.player_id
        else:
            player_id = -1

        self.reasons[player_id] = self.reasons[player_id][-7:] + [text]

    def Set(self, player: 'Player|None|User', text: 'EffectFailure'):
        self.SetText(player, text)

    def __repr__(self) -> str:
        if self.effect.ability.flags.is_statistics:
            return "(None)"

        player_ids = [-1, 0, 1, 2, 3]
        reasons: Dict[int, str] = {}
        for player_id in player_ids:
            failure = self.reasons[player_id][-1]
            if isinstance(failure, EffectFailure):
                reasons[player_id] = failure.value
            else:
                reasons[player_id] = failure
        return f"{reasons}"

    ################################################################################
    #
    def IsFailure(self, player_id: int) -> bool:
        return bool(self.reasons[player_id][-1])

    def GetText(self, player_id: int) -> str:
        return self.reasons[player_id][-1]

    def IsNoProcess(self, player_id: int) -> bool:
        return self.reasons[player_id] == [EffectFailure.NoProcess] and \
            self.reasons[-1][-1] == ""
