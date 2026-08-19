from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.AfterSchemeRemoveThreat(
            AbilityType.ForcedResponse,
            "This",
            lambda effect, message: effect.this.PlaceThreatOnSchemes([effect.this], 1, effect),
        ),
    ]
