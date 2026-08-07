from . import *

# * Exodus

def GetAbilities() -> Sequence['Ability']:

    def exodus(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> None:
        this = effect.this.CastTo(Minion)
        Unused(this)

        player = message.GetAgainstPlayer()

        if player:
            values = [
                attack_message.would_atk_unit_message.attack_damage
                for attack_message in message.atk_messages
                if attack_message.would_atk_unit_message is not None
            ]
            value = max(values, default=0)
            player.DiscardDeckTopCards(value, effect)


    return [
        AbilityFactory.AfterUnitAttackYou(
            AbilityType.ForcedResponse,
            "This",
            exodus
        ),
    ]
