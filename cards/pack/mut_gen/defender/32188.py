from . import *


# Heroic Intervention

def GetAbilities() -> Sequence['Ability']:
    def heroic_intervention(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        effect.this.RemoveThreatFromSchemesTotal(effect.targets, 5, effect)
        Faces.GiveStatus([effect.GetInitiator().GetIdentity()], "Tough", effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            heroic_intervention,
        ).SetCost(Cost("3"))
        .SetCostFunc(CostFunc.RemoveFromGame("This"))
        .SetCostFunc(CostFunc.RemoveFromCampaignLog("This"))
        .SetTarget(Scheme2, range=(1, 5), repeat_rules="Threat"),
    ]
