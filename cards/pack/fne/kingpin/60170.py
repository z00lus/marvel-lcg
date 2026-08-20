from . import *


def GetAbilities() -> Sequence['Ability']:
    def attack(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        message.GetAgainstPlayer().GetIdentity().TakeDamage(effect.this, 1, effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        message.GetToPlayer().GetIdentity().TakeDamage(effect.this, 1, effect)

    return [
        AbilityFactory.WhenUnitWouldAttack(
            AbilityType.ForcedInterrupt,
            "This",
            attack,
        ),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
