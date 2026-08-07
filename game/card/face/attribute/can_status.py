from . import *

class CanStatus(HasVulnerable, HasSteady, HasToughness, HasStalwart):
    BASE_MAX_TOUGH = 1

    DISCARD_RULE = Literal["All", "Steady"]|int

    @override
    def __init__(self, paper: 'Paper') -> None:
        super().__init__(paper)

    def ResetStates(self):
        self.components.status.OnParentReset()

    @override
    def OnReset(self, message: 'Message.WhenCardReset_Text') -> None:
        if not message.is_flip:
            self.ResetStates()
        return super().OnReset(message)

    @override
    def OnAfterCardLeavePlay(self, message: 'Message.AfterCardLeavePlay') -> None:
        self.ResetStates()
        return super().OnAfterCardLeavePlay(message)

    ################################################################################
    #
    @property
    def confused(self) -> int:
        return self.components.status.confused
    @property
    def stunned(self) -> int:
        return self.components.status.stunned
    @property
    def tough(self) -> int:
        return self.components.status.tough

    @property
    def tough_max(self) -> int:
        from game.message import Message
        from game.card.face.base import Unit2

        value = CanStatus.BASE_MAX_TOUGH
        message = Message.GettingUnitAdditionalTough(self.card.CastTo(Unit2))
        message.Send()
        additional = message.return_value
        if additional:
            value += additional
        return value

    # @property
    # def stun_max(self) -> int:
    #     return 1

    # @property
    # def confuse_max(self) -> int:
    #     return 1

    # @staticmethod
    # def ToCounterName(name: str) -> 'CardFace.COUNTER':
    #     return Cast(CardFace.COUNTER, {
    #         'Confused': 'confused',
    #         'Stunned': 'stunned',
    #         'Tough': 'tough',
    #     }[name])

    def GainStatus(self, name: "CardFace.STATUS", by_effect: 'Effect', *, override_cannot: bool=False) -> bool:
        from game.message import Message

        if not self.card.IsOnField():
            #  or self.card.face.IsDefeated():
            return False
        # assert name in ['tough', 'stunned', 'confused'], f"{name=}"
        # This opt-in is only for card text that explicitly overrides a
        # prohibition under the Golden Rule. Ordinary effects must leave it
        # false so "cannot" remains absolute.
        if name == "Confused":
            if override_cannot:
                if self.IsConfused():
                    return False
            elif not self.CanbeConfused():
                return False
        if name == "Stunned":
            if override_cannot:
                if self.IsStunned():
                    return False
            elif not self.CanbeStunned():
                return False
        if name == "Tough" and self.IsTough() and self.tough >= self.tough_max:
            return False

        would_message = Message.WhenStatusWouldCardPlaceOn(self, name, by_effect)
        would_message.Send()
        if would_message.is_be_instead:
            return False

        status_face = self.components.status.GiveStatusCard(name, by_effect)
        placed_message = Message.AfterStatusCardPlaceOn(status_face, would_message)
        placed_message.Send()

        return True

    def LoseState(self, name: "CardFace.STATUS", by_effect: 'Effect', rule: DISCARD_RULE) -> int:
        if not self.card.IsOnField():
            return False
        return self.components.status.DiscardStatusCard(name, by_effect, rule)

    # def GainConfused(self, by_effect: 'Effect') -> bool:
    #     return self.GainStatus("Confused", by_effect)
    # def GainStunned(self, by_effect: 'Effect') -> bool:
    #     return self.GainStatus("Stunned", by_effect)
    # def GainTough(self, by_effect: 'Effect') -> bool:
    #     return self.GainStatus("Tough", by_effect)

    def DiscardConfused(self, by_effect: 'Effect', *, rule: 'DISCARD_RULE') -> int:
        return self.LoseState("Confused", by_effect, rule)
    def DiscardStunned(self, by_effect: 'Effect', *, rule: 'DISCARD_RULE') -> int:
        return self.LoseState("Stunned", by_effect, rule)
    def DiscardTough(self, by_effect: 'Effect', *, rule: 'DISCARD_RULE') -> int:
        return self.LoseState("Tough", by_effect, rule)

    def DiscardAllTough(self, by_effect: 'Effect') -> int:
        return self.DiscardTough(by_effect, rule="All")

    def DiscardEachStatus(self, by_effect: 'Effect'):
        self.DiscardConfused(by_effect, rule="All")
        self.DiscardStunned(by_effect, rule="All")
        self.DiscardAllTough(by_effect)

    def IsConfused(self) -> bool:
        from game.card.face.base import Unit2
        if self.card.CastTo(Unit2).IsSteady():
            return self.confused > 1
        else:
            return self.confused > 0
    def IsTough(self) -> bool:
        return self.tough != 0
    def IsStunned(self) -> bool:
        from game.card.face.base import Unit2
        if self.card.CastTo(Unit2).IsSteady():
            return self.stunned > 1
        else:
            return self.stunned > 0

    def CanGainTough(self) -> bool:
        if not self.IsInPlay():
            return False
        return self.tough < self.tough_max

    def CanbeStunned(self) -> bool:
        if not self.IsInPlay():
            return False
        if self.IsStalwart():
            return False
        if self.IsStunned():
            return False
        if self.GetBuff(BuffCannotBeStunned):
            return False
        return True

    def CanbeConfused(self) -> bool:
        if not self.IsInPlay():
            return False
        if self.IsStalwart():
            return False
        if self.IsConfused():
            return False
        if self.GetBuff(BuffCannotBeConfused):
            return False
        return True

    ################################################################################
    #
    # def CopyStates(self, unit: 'Unit2') -> bool:
    #     from game.card.face.component.unit_state import UnitState
    #     if self.GetComponent(UnitState).CopyStates(unit.GetComponent(UnitState)):
    #         Send.UnitCopyState_Text(self, unit)
    #         return True
    #     else:
    #         return False

    def HasStatus(self, name: "CardFace.STATUS|Literal['Any']") -> bool:
        if name == "Any":
            return self.confused > 0 or self.stunned > 0 or self.tough > 0
        if name == "Confused":
            return self.confused > 0
        if name == "Stunned":
            return self.stunned > 0
        if name == "Tough":
            return self.tough > 0
        assert False, f"{self=} {name=}"

    def GetStatusSize(self) -> int:
        return self.components.status.GetStatusSize()

class CanNoStatus(CanStatus):
    @override
    def CanGainTough(self) -> bool:
        return False

    @override
    def CanbeStunned(self) -> bool:
        return False

    @override
    def CanbeConfused(self) -> bool:
        return False
