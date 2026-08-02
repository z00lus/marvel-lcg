from . import *


# Swagger

def GetAbilities() -> Sequence['Ability']:
    def swagger(effect: 'Effect', message: 'Message.WhenUnitWouldDefend') -> None:
        message.GainDEFForThisAttack(3, effect)
        Faces.ReadyAll([message.trigger], effect)

    return [
        AbilityFactory.WhenUnitDefendAgainstAttack(
            AbilityType.HeroInterrupt,
            "You",
            swagger,
            is_basic_defense=True,
        ).SetCostFunc(CostFunc.RemoveFromGame("This"))
        .SetCostFunc(CostFunc.RemoveFromCampaignLog("This")),
    ]
