from . import *


# Surprise!

def GetAbilities() -> Sequence['Ability']:
    def surprise(effect: 'Effect', message: 'Message.AfterUnitThwartEnd') -> None:
        player = effect.GetInitiator()
        effect.this.RemoveThreatFromSchemesTotal(effect.targets, 3, effect)
        enemy = player.AskChooseFace(Worlds.GetOnFieldEnemies(effect), effect, prompt="Choose an enemy to confuse")
        if enemy:
            Faces.GiveStatus([enemy], "Confused", effect)

    return [
        AbilityFactory.AfterUnitMakeThwart(
            AbilityType.HeroResponse,
            "You",
            surprise,
        ).SetCostFunc(CostFunc.RemoveFromGame("This"))
        .SetCostFunc(CostFunc.RemoveFromCampaignLog("This"))
        .SetTarget(Scheme2, range=(1, 3), repeat_rules="Threat"),
    ]
