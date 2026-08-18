from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        Find.FindAndReveal(
            effect,
            message.GetToPlayer(),
            name="Deranged Bloodlust",
            card_type=SchemeSide2,
        )

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        BullseyeActivationAbility(),
    ]
