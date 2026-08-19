from . import *


def GetAbilities() -> Sequence['Ability']:

    def j_jonah_jameson(
        effect: 'Effect',
        message: 'Message.WhenPlayerInTurn',
    ) -> None:
        effect.GetInitiator().DrawUp(2, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            j_jonah_jameson,
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetCostFunc(CostFunc.Counter("This", 1, STAMINA))
        .SetCostFunc(CostFunc.DealPlayerEncounterCard(1, "Initiator")),
    ]
