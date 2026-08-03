from . import *


def GetAbilities() -> Sequence['Ability']:
    def secure_the_landing_pad(
        effect: 'Effect',
        message: 'Message.WhenSchemeBeDefeated',
    ) -> None:
        effect.this.CastTo(EncounterSideScheme).card.Flip(effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            secure_the_landing_pad,
        ),
    ]
