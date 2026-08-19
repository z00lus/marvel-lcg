from . import *


def GetAbilities() -> Sequence['Ability']:

    def activate_all(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        enemies: List['Enemy'] = []
        villain = Worlds.FindVillain(effect)
        if villain:
            enemies.append(villain)
        enemies += player.engaged_minions.GetAll()

        for enemy in enemies:
            def gain_aerial_bonus(
                activate_message: 'Message.WhenEnemyActivateAgainstYou',
                activating_enemy: 'Enemy'=enemy,
            ) -> None:
                if activating_enemy.HasTrait("AERIAL"):
                    activating_enemy.GainForThisActive(
                        effect,
                        activate_message.would_message,
                        attack=2,
                        scheme=2,
                    )

            enemy.DoActivate(player, effect, operation=gain_aerial_bonus)

    return [AbilityFactory.WhenThisRevealed(None, activate_all)]
