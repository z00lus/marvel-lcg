from . import *


def GetAbilities() -> Sequence['Ability']:
    def summoned_back(
        effect: 'Effect',
        message: 'Message.WhenCardRevealed',
    ) -> None:
        player = message.GetToPlayer()
        minion = Search.EncounterCard(
            effect,
            player,
            include_discard_pile=True,
            include_set_aside=True,
            card_type=Minion,
            is_nemesis=player,
        )
        if minion:
            minion.PutIntoPlay(player, effect)
        Worlds.GetEncounterDeck(effect).Shuffle(effect)

    return [
        AbilityFactory.WhenThisRevealed(None, summoned_back),
    ]
