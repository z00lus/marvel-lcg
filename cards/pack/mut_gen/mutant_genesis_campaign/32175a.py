from . import *


# Magneto's Fortress

def GetAbilities() -> Sequence['Ability']:
    def magnetos_fortress(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        ShuffleRandomFuturePastCardIntoEncounterDeck(effect)
        this.card.Flip(effect)

        magneto = Worlds.FindVillain(effect, name="Magneto")
        magnetos_power = this.card.face
        if magneto and Attachment.IsType(magnetos_power):
            magnetos_power.AttachTo2(magneto, effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            magnetos_fortress,
        ),
    ]
