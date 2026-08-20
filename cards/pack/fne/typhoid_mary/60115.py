from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        FlipMaryWalkerToTrust(effect, player)
        villain = Worlds.FindVillain(effect)
        if villain:
            villain.DoSchemes(player, effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        if not IsActivatingMary(message, "Typhoid Mary"):
            return
        player = message.GetToPlayer()
        ally = Filter.One(player.GetControlAllies(), effect)
        if ally:
            ally.TakeDamage(effect.this, 3, effect)

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
