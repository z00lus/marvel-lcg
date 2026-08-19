from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        minion = Worlds.DiscardEncounterCardsUntil(
            effect,
            trait="TRACKSUIT",
            card_type=Minion,
        )
        if minion:
            effect.this.CastTo(EncounterSideScheme).PlaceCardHere(minion, False, effect)

    def tracksuit_revealed(effect: 'Effect', message: 'Message.AfterCardRevealedEnd') -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        tucked = this.GetPlacedCardArea().FindCards(card_type=Minion)
        if not tucked:
            return
        player = message.GetToPlayer()
        minion = tucked[0] if len(tucked) == 1 else player.AskChooseFace(
            tucked,
            effect,
            prompt="Choose a tucked TRACKSUIT minion to reveal",
        )
        if minion:
            minion.Reveal(player, effect)

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.AfterPlayerRevealCard(
            AbilityType.ForcedResponse,
            "AnyPlayer",
            CardFinder(trait="TRACKSUIT", card_type=Minion),
            tracksuit_revealed,
            conditions=[lambda effect, message: message.reveal_message.IsFromEncounterDeck()],
        ),
    ]
