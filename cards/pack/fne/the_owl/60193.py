from . import *


def GetAbilities() -> Sequence['Ability']:

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        if message.would_atk_message:
            message.would_atk_message.GainPiercing(effect)

    return [
        PiercingAttackAbility(),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            boost,
            during_attack=True,
        ),
    ]
