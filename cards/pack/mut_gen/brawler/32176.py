from . import *


# Coup de Grâce

def GetAbilities() -> Sequence['Ability']:
    def coup_de_grace(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        message.GainATKForThisAttack(3, effect)
        message.GainOverKill(effect)

    return [
        AbilityFactory.WhenUnitMakeAttack(
            AbilityType.HeroInterrupt,
            "You",
            coup_de_grace,
        ).SetCostFunc(CostFunc.RemoveFromGame("This"))
        .SetCostFunc(CostFunc.RemoveFromCampaignLog("This")),
    ]
