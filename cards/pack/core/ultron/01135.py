from . import *

# * Ultron (II)

def GetAbilities() -> Sequence['Ability']:

    def ultron(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        for target in message.attacked_targets:
            player = target.GetControlByPlayer()
            CreateUltronFacedownDrone(player, 1, effect)

    def ultron_attack(effect: 'Effect', message: 'Message.WhenCalculateAttackDamage') -> int:
        player = message.would_atk_message.property.against_player
        if player:
            return len([x for x in player.GetEngagedMinions() if x.HasTrait("DRONE")])
        return 0

    return [
        AbilityFactory.WhenUnitAttackYou(
            AbilityType.ForcedInterrupt,
            "This",
            ultron,
        ),
        *AbilityFactory.UnitGetATKWhileAttacking(
            AbilityType.ForcedInterrupt,
            "This",
            None,
            ultron_attack
        )
    ]
