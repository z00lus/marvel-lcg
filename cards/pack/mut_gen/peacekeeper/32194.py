from . import *


# Mentorship

def GetAbilities() -> Sequence['Ability']:
    def mentorship(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        effect.this.RemoveThreatFromSchemesTotal(effect.targets, 5, effect)
        Faces.ReadyAll(player.GetControlAllies(), effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            mentorship,
        ).SetCost(Cost("3"))
        .SetCostFunc(CostFunc.RemoveFromGame("This"))
        .SetCostFunc(CostFunc.RemoveFromCampaignLog("This"))
        .SetTarget(Scheme2, range=(1, 5), repeat_rules="Threat"),
    ]
