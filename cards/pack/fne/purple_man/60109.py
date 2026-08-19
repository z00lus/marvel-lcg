from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        minions = Worlds.GetEncounterDiscardPileCards(
            effect,
            INFLUENCED_MINION,
        )
        if not minions:
            ThisCardGainSurge(effect)
            return
        minion = minions[0] if len(minions) == 1 else player.AskChooseFace(minions, effect)
        if minion:
            minion.Reveal(player, effect)

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        PurpleManBoostAbility(),
    ]
