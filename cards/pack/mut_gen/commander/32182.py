from . import *


# Compassion

def GetAbilities() -> Sequence['Ability']:
    def compassion(effect: 'Effect', message: 'Message.AfterUnitRecovery') -> None:
        player = effect.GetInitiator()
        player.AssignHeal(player.GetControlCharacters(), 3, effect)
        player.DrawUp(1, effect)

    return [
        AbilityFactory.AfterUnitMakeRecovery(
            AbilityType.AlterEgoResponse,
            "You",
            compassion,
        ).SetCostFunc(CostFunc.RemoveFromGame("This"))
        .SetCostFunc(CostFunc.RemoveFromCampaignLog("This")),
    ]
