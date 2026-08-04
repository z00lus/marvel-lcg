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
        ).SetCostFunc(CostFunc.Exhaust("YourIdentity")),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.AlterEgoAction,
        ).SetCostFunc(CostFunc.Discard(
            Select.From(lambda effect: GetIonicCards(effect), range=(3, 3))
        )),
    ]
