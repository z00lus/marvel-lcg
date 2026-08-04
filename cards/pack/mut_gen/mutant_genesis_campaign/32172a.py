from . import *


# Enemy of My Enemy

def GetAbilities() -> Sequence['Ability']:
    def enemy_of_my_enemy(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        ShuffleRandomFuturePastCardIntoEncounterDeck(effect)
        this.card.Flip(effect)
        this.card.face.PutIntoPlay(
            Worlds.GetFirstPlayer(effect),
            effect,
            under_control=True,
        )

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            enemy_of_my_enemy,
        ),
    ]
