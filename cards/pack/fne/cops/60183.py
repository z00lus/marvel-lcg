from . import *


def GetAbilities() -> Sequence['Ability']:

    def defeated(effect: 'Effect', message: 'Message.AfterUnitBeDefeated') -> None:
        if message.attacker:
            player = message.attacker.GetControlByPlayer()
            if player:
                player.DealEncounterCards(1, effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        this = effect.this.CastTo(Minion)
        message.GetToPlayer().GetIdentity().TakeIndirectDamage(this, 2, effect)

    return [
        AbilityFactory.AfterUnitBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            defeated,
        ),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
