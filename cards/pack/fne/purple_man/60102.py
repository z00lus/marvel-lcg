from . import *


def GetAbilities() -> Sequence['Ability']:
    def defeated(effect: 'Effect', message: 'Message.WhenUnitBeDefeated') -> None:
        main_scheme = Worlds.FindMainScheme(effect)
        if main_scheme:
            effect.this.PlaceThreatOnSchemes([main_scheme], 3, effect)

    return [
        AbilityFactory.WhenUnitBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            defeated,
        ),
        PurpleManBoostAbility(),
    ]
