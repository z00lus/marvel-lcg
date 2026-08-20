from . import *


def GetAbilities() -> Sequence['Ability']:
    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        message.GiveAdditionalBoostCardForThisActivation(1, effect)

    return [AbilityFactory.WhenCardBecomeBoost("This", boost)]
