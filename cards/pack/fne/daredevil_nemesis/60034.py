from . import *

# Deadliest Man Alive


def GetAbilities() -> Sequence['Ability']:

    def deadliest_man_alive(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        Faces.GiveFacedownBoostCards([message.trigger], 1, effect)

    return [
        AbilityFactory.WhenUnitWouldAttack(
            AbilityType.ForcedInterrupt,
            CardFinder(name="Bullseye"),
            deadliest_man_alive,
        ),
    ]
