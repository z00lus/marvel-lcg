from . import *


def GetAbilities() -> Sequence['Ability']:

    def ben_urich(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        cards = player.LookAtDeck("EncounterDeck", 2, effect)
        player.AskDiscardFaces(cards, (0, 1), effect, not_shuffle=True)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            ben_urich,
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetCostFunc(CostFunc.Counter("This", 1, STAMINA)),
    ]
