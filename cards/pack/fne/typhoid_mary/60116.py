from . import *


def GetAbilities() -> Sequence['Ability']:
    def stun_identity(effect: 'Effect', player: 'Player') -> None:
        Faces.GiveStatus([player.GetIdentity()], "Stunned", effect)

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        for character in list(player.GetControlCharacters()):
            character.TakeDamage(effect.this, 1, effect)
        stun_identity(effect, player)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        if IsActivatingMary(message, "Typhoid Mary"):
            stun_identity(effect, message.GetToPlayer())

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
