from . import *

# Heightened Hearing


def GetAbilities() -> Sequence['Ability']:

    def heightened_hearing(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        player = effect.GetInitiator()
        Faces.DiscardAll([effect.this], effect)
        message.GainATKForThisAttack(-3, effect)
        message.property.against_player = player
        message.ReplaceTarget(player.GetIdentity())

    return [
        AbilityFactory.CanPlayThisUpgradeCard(Enemy),
        AbilityFactory.WhenUnitWouldAttack(
            AbilityType.HeroInterrupt,
            "AttachedEnemy",
            heightened_hearing,
        ).SetLabel("defense"),
    ]
