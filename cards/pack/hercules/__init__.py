from cards.pack import *


LABOR_DECK = "hercules_labor"
GIFT_DECK = "hercules_gift"


def GetHerculesDeck(player: 'Player', name: str) -> 'Deck|None':
    return player.special_decks.get(name)


def GetLaborDeck(player: 'Player') -> 'Deck|None':
    return GetHerculesDeck(player, LABOR_DECK)


def GetGiftDeck(player: 'Player') -> 'Deck|None':
    return GetHerculesDeck(player, GIFT_DECK)


def CountGifts(player: 'Player') -> int:
    return len(player.GetControlCards(CardFinder(trait="GIFT")))


def ReturnLaborToDeckWhenItLeavesPlay() -> 'Ability':
    # Hercules FAQ: a Labor that leaves play outside the victory display
    # is placed on the bottom of its owner's Labor deck.
    def return_labor(effect: 'Effect', message: 'Message.AfterCardLeavePlay') -> None:
        if message.into_area.flags.is_victory_display:
            return

        labor_deck = GetLaborDeck(effect.this.GetOwnerPlayer())
        if labor_deck:
            Faces.MoveAllToDeck([effect.this], labor_deck, "Bottom", effect)

    return AbilityFactory.AfterCardLeavePlay(
        AbilityType.ForcedResponse,
        "This",
        return_labor,
    )


def SetupHerculesSpecialDecks(effect: 'Effect', message: 'Message.WhenPlayerSelectHero') -> None:
    from game.message import Message

    player = effect.GetInitiator()
    if GetLaborDeck(player) or GetGiftDeck(player):
        return

    labor_deck = Deck2(player, DeckType.AdditionalDeck, CardFace)
    gift_deck = Deck2(player, DeckType.AdditionalDeck, CardFace)
    player.special_decks[LABOR_DECK] = labor_deck
    player.special_decks[GIFT_DECK] = gift_deck

    set_aside = player.set_aside_deck.Get()
    labors = CardFinder(trait="LABOR").Checks(set_aside)
    gifts = CardFinder(trait="GIFT").Checks(set_aside)
    Faces.MoveAllTo(labors, labor_deck, effect)
    Faces.MoveAllTo(gifts, gift_deck, effect)
    Message.WhenDeckCreated_Text(labor_deck)
    Message.WhenDeckCreated_Text(gift_deck)
    labor_deck.Shuffle(effect)
    gift_deck.Shuffle(effect)
