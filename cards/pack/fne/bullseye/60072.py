from . import *


def GetAbilities() -> Sequence['Ability']:

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        message.GiveActivatingEnemyAdditionalBoostCard(1, effect)

    return [
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            boost,
            during_attack=True,
            is_undefended_attack=True,
        ),
    ]
