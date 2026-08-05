from . import *

# * Ghost Rider


def GetAbilities() -> Sequence['Ability']:

    def ghost_rider(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> None:
        Faces.GiveStatus([message.target], "Confused", effect)

    return [
        AbilityFactory.WhenUnitWouldAttackUnit(
            AbilityType.Interrupt,
            "This",
            Minion,
            ghost_rider,
        ).SetCostFunc(CostFunc.Spend(Cost("Y"))),
        AbilityFactory.WhenUnitWouldAttackUnit(
            AbilityType.Interrupt,
            "This",
            Villain,
            ghost_rider,
        ).SetCostFunc(CostFunc.Spend(Cost("YY"))),
    ]
