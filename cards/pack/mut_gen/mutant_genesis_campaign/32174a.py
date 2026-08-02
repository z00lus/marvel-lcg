from . import *


# Surprise Attack

def GetAbilities() -> Sequence['Ability']:
    def surprise_attack(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        ShuffleRandomFuturePastCardIntoEncounterDeck(effect)
        this.card.Flip(effect, call_reveal=False)
        player = message.GetDefeatingPlayer()
        Faces.MoveAllTo([this.card.face], player.obligations_area, effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            surprise_attack,
            has_defeating_player=True,
        ),
    ]
