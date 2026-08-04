from . import *

# * Kingpin


def GetAbilities() -> Sequence['Ability']:

    def kingpin(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        message.DoSchemeInstead(effect)

    return [
        AbilityFactory.WhenUnitAttackYou(
            AbilityType.ForcedInterrupt,
            "This",
            kingpin,
            conditions=[
                lambda effect, message:
                    message.property.against_player is not None and
                    message.property.against_player.IsName("Maya Lopez")
            ],
        ),
    ]
