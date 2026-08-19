from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        Faces.ExhaustAll(GetDailyBugleSupports(effect), effect)

    return [
        *AbilityFactory.PlayersCannotReadyCardWhile(
            "AnyPlayer",
            DAILY_BUGLE_SUPPORT,
            control_by="AnyPlayer",
        ),
        AbilityFactory.WhenThisRevealed(None, revealed),
    ]
