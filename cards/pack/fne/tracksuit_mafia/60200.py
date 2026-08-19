from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.WhenThisRevealed(
            None,
            lambda effect, message: effect.this.PlaceAccelerationToken(1, effect),
        ),
        AbilityFactory.AfterUnitSchemeEnd(
            AbilityType.ForcedResponse,
            "This",
            lambda effect, message: effect.this.PlaceAccelerationToken(1, effect),
        ),
    ]
