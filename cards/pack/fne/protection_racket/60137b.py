from . import *


class PawnShopDiscount(Buff):
    @override
    def __init__(self) -> None:
        super().__init__()
        self.played_upgrade = False

    @override
    def OnRecordPlayedFace(self, face: 'CardFace') -> None:
        super().OnRecordPlayedFace(face)
        if Upgrade.IsType(face):
            self.played_upgrade = True

    @override
    def OnRoundEnd(self) -> None:
        super().OnRoundEnd()
        self.played_upgrade = False

    def __bool__(self) -> bool:
        return not self.played_upgrade


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.ReduceCostToPlayFaceWhen(
            Upgrade,
            1,
            "AnyPlayer",
            conditions=[lambda effect, message: bool(effect.this.GetBuff(PawnShopDiscount))],
        ),
        AbilityFactory.AfterCardEnterPlay(
            AbilityType.ForcedResponse,
            CardFace,
            lambda effect, message: PlaceThreatHere(effect),
            conditions=[lambda effect, message:
                Attachment.IsType(message.trigger) or Upgrade.IsType(message.trigger)],
        ),
    ]
