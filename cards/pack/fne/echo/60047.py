from . import *

# Muscle Memory


def GetAbilities() -> Sequence['Ability']:

    def muscle_memory(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        initiator = effect.GetInitiator()
        Faces.AddToHand(effect.targets, initiator, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            muscle_memory,
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetTarget("TuckUnderYourIdentityCard", card_type=Event),
    ]
