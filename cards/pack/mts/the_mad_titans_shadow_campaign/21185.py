from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.AlterEgoAction,
            lambda effect, message: None,
        ).SetCost(Cost("1"))
        .SetCostFunc(CostFunc.RemoveFromGame("This"))
        .CanWorkOnlyInHand(),
    ]
