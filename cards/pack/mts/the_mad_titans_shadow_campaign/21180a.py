from . import *


def GetAbilities() -> Sequence['Ability']:
    def secure_the_landing_pad(
        effect: 'Effect',
        message: 'Message.WhenSchemeBeDefeated',
    ) -> None:
        this = effect.this.CastTo(EncounterSideScheme)
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
            secure_the_landing_pad,
        ),
    ]
