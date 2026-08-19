from . import *


def GetAbilities() -> Sequence['Ability']:
    def after_scheme(effect: 'Effect', message: 'Message.AfterUnitSchemeEnd') -> None:
        face = Worlds.PopEncounterCard(effect)
        if face:
            effect.this.CastTo(Minion).GiveBoostCard(face, effect)

    return [
        AbilityFactory.AfterUnitSchemeEnd(
            AbilityType.ForcedResponse,
            "This",
            after_scheme,
        ),
    ]
