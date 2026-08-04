from . import *

# Pacifism


def GetAbilities() -> Sequence['Ability']:
    return [
        *AbilityFactory.UnitCannotAttackTarget(
            CardFinder(name="Wonder Man", card_type=Identity),
            cannot_attack=True,
        ),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.AlterEgoAction,
        ).SetName("Exhaust Simon Williams")
        .SetCostFunc(CostFunc.Exhaust("YourIdentity")),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.AlterEgoAction,
        ).SetName("Discard 3 cards tucked under Ionic Physiology")
        .SetCostFunc(CostFunc.Discard(
            Select.From(lambda effect: GetIonicCards(effect), range=(3, 3))
        )),
    ]
