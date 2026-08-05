from . import *

# * Elektra


def GetAbilities() -> Sequence['Ability']:

    def elektra(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        message.ChangeDealtToTarget(effect.GetInitiator().GetHero(), effect)

    return [
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.ForcedInterrupt,
            "This",
            elektra,
            is_consequential_damage=True,
            conditions=[
                lambda effect, message: effect.GetInitiator().IsHero()
            ],
        ),
    ]
