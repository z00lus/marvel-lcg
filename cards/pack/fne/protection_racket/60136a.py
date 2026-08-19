from . import *


def GetAbilities() -> Sequence['Ability']:
    return [AbilityFactory.WhenCardSetup("This", lambda effect, message: SelectProtectionRacketScheme(effect))]
