from . import *


def GetAbilities() -> Sequence['Ability']:
    def defeated(effect: 'Effect', message: 'Message.WhenUnitBeDefeated') -> None:
        player = message.GetKillerPlayer()
        if player:
            identity = player.GetIdentity()
            identity.TakeDamage(effect.this, 3, effect)

    return [
        AbilityFactory.WhenUnitBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            defeated,
            has_defeating_player=True,
        ),
        PurpleManBoostAbility(),
    ]
