from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.WhenThisRevealed(None, lambda effect, message: SwapProtectionRacketScheme(effect)),
        AbilityFactory.WhenCardBecomeBoost("This", lambda effect, message: SwapProtectionRacketScheme(effect)),
    ]
