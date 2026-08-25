from . import *


def GetAbilities() -> Sequence['Ability']:

    def luke_cage(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        Faces.GiveStatus([effect.this], "Tough", effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            luke_cage,
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetCostFunc(CostFunc.DealDamage(1, "This")),
    ]
