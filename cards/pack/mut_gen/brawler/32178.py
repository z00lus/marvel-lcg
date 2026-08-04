from . import *


# Brazen Defense

def GetAbilities() -> Sequence['Ability']:
    def brazen_defense(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        message.PreventDamage(3, effect)
        effect.this.DealDamage([message.source], 3, effect)

    return [
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.HeroInterrupt,
            Friend,
            brazen_defense,
            is_from_attack=True,
            who_deal_damage=Enemy,
        ).SetCost(Cost("1"))
        .SetCostFunc(CostFunc.RemoveFromGame("This"))
        .SetCostFunc(CostFunc.RemoveFromCampaignLog("This")),
    ]
