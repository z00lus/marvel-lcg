from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        minion = Worlds.FindCardOnField(effect, card_type=Minion, is_nemesis=player)
        if minion:
            minion.DoActivate(player, effect)
            return
        minion = FindNemesisMinion(effect, player)
        if minion:
            minion.Reveal(player, effect)
        else:
            FindAndRevealUnderling(effect, player)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        if isinstance(message.being_message, Message.WhenUnitBeingAttack):
            message.being_message.would_atk_message.GainOverKill(effect)

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardBecomeBoost("This", boost, during_attack=True),
    ]
