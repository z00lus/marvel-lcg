from . import *


# Frightened Police

def GetAbilities() -> Sequence['Ability']:
    def frightened_police(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        ShuffleRandomFuturePastCardIntoEncounterDeck(effect)
        this.card.Flip(effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            frightened_police,
        ),
    ]
