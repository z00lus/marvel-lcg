from . import *


def GetAbilities() -> Sequence['Ability']:

    def setup(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        daily_bugle = effect.world.aside_deck.FindCard(card_ids=["60152"])
        if daily_bugle:
            daily_bugle.PutIntoPlay("FirstPlayer", effect)

        candidates = effect.world.aside_deck.FindCards(
            DAILY_BUGLE_SUPPORT,
        )
        for player in Worlds.GetPlayers(effect):
            if not candidates:
                break
            chosen = Rand.RandomChoice(candidates, effect)
            candidates.remove(chosen)
            # Support.OnPutIntoPlay moves the card to this player's support
            # area, which establishes control.  Do not use under_control here:
            # these remain encounter-owned cards and must never enter the
            # player's ordinary discard pile.
            chosen.PutIntoPlay(player, effect)

        Faces.RemoveAllFromGame(candidates, effect)

    return [AbilityFactory.WhenCardSetup("This", setup)]
