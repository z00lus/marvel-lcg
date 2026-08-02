from . import *


# Determined Defense

def GetAbilities() -> Sequence['Ability']:
    def determined_defense(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        damage = message.will_take_damage
        message.PreventDamage("All", effect)
        main_scheme = Worlds.FindMainScheme(effect)
        if main_scheme:
            effect.this.RemoveThreatFromSchemes([main_scheme], damage, effect)

    return [
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.HeroInterrupt,
            "You",
            determined_defense,
            is_from_attack=True,
            while_defending=True,
        ).SetCost(Cost("2"))
        .SetCostFunc(CostFunc.RemoveFromGame("This"))
        .SetCostFunc(CostFunc.RemoveFromCampaignLog("This")),
    ]
