from . import *


# Ferocious Attack

def GetAbilities() -> Sequence['Ability']:
    def ferocious_attack(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        effect.this.DealDamage(effect.targets, 6, effect, property=AttackProperty())
        Faces.ReadyAll([effect.GetInitiator().GetHero()], effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            ferocious_attack,
        ).SetCost(Cost("3"))
        .SetCostFunc(CostFunc.RemoveFromGame("This"))
        .SetCostFunc(CostFunc.RemoveFromCampaignLog("This"))
        .SetTarget(Enemy),
    ]
