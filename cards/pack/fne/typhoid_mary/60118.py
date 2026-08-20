from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        FlipMaryWalkerToTrust(effect, player)
        villain = Worlds.FindVillain(effect)
        if villain:
            villain.DoAttackYou(player, effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        if IsActivatingMary(message, "Bloody Mary"):
            message.GetToPlayer().GetIdentity().TakeDamage(effect.this, 2, effect)

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
