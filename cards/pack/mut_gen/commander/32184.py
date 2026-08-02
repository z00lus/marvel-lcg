from . import *


# Shock and Awe

def GetAbilities() -> Sequence['Ability']:
    def shock_and_awe(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        effect.this.DealDamage(effect.targets, 6, effect, property=AttackProperty())
        Faces.ReadyAll(player.GetControlAllies(), effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            shock_and_awe,
        ).SetCost(Cost("3"))
        .SetCostFunc(CostFunc.RemoveFromGame("This"))
        .SetCostFunc(CostFunc.RemoveFromCampaignLog("This"))
        .SetTarget(Enemy),
    ]
