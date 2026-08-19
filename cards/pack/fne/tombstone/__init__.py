from cards.pack import *


def AttachToHighestHpMinionAndGiveTough() -> 'Ability':
    return AbilityFactory.AttachToFaceWhenPutIntoPlay(
        Minion,
        highest_printed_hp=True,
        if_cannot_gain_surge=True,
        when_attach_operation=lambda face, effect:
            Faces.GiveStatus([face], "Tough", effect),
    )
