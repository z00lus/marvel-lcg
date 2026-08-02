from . import *


# Magneto's Fortress

def GetAbilities() -> Sequence['Ability']:
    def magnetos_fortress(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        ShuffleRandomFuturePastCardIntoEncounterDeck(effect)
        this.card.Flip(effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            magnetos_fortress,
        ),
    ]
