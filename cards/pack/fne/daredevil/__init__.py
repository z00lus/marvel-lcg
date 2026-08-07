from cards.pack import *


SENSE_DECK = "daredevil_sense"
SENSE_CARD_IDS = ["60002", "60003", "60004", "60005", "60006"]


def GetSenseDeck(player: 'Player') -> 'Deck|None':
    return player.special_decks.get(SENSE_DECK)


def RevealSenseDeck(top: 'CardFace', effect: 'Effect') -> None:
    Unused(top)
    sense_deck = GetSenseDeck(effect.GetInitiator())
    if not sense_deck:
        return

    # The Sense deck has a fixed, inspectable order. Every card is faceup,
    # although Daredevil's Superhuman Senses can play only its top card.
    for sense in sense_deck.GetAll():
        sense.card.can_state.is_like_in_hand = None
        sense.FlipTo(effect, face_up=True, ui_look_at=False)


def SetupSenseDeck(effect: 'Effect', message: 'Message.WhenPlayerSelectHero') -> None:
    from game.message import Message

    player = effect.GetInitiator()
    if GetSenseDeck(player):
        return

    sense_deck = Deck2(player, DeckType.AdditionalDeck, CardFace)
    player.special_decks[SENSE_DECK] = sense_deck

    senses = CardFinder(trait="SENSE").Checks(player.set_aside_deck.Get())
    Faces.MoveAllTo(senses, sense_deck, effect)
    Message.WhenDeckCreated_Text(sense_deck)
    sense_deck.Shuffle(effect)


def ReturnSenseCardsToDeck() -> Sequence['Ability']:
    def return_sense_to_deck(effect: 'Effect', message: 'Message.WhenCardWouldLeavePlay') -> None:
        deck = GetSenseDeck(effect.GetInitiator())
        if not deck or message.into_area == deck:
            return

        message.SetBeInstead(effect)
        Faces.MoveAllToDeck([message.trigger], deck, "Bottom", effect)

    return [
        AbilityFactory.WhenCardWouldLeavePlay(
            AbilityType.ForcedInterrupt,
            CardFinder(trait="SENSE"),
            return_sense_to_deck,
            conditions=[
                lambda effect, message:
                    message.trigger.GetOwnerPlayer() == effect.GetInitiator()
            ],
        ),
    ]


def GetAttachedUpgradeCount(face: 'CardFace') -> int:
    return len(face.GetInventoryDeck().FindCards(card_type=Upgrade))


def ChooseAndPlaySense(player: 'Player', effect: 'Effect', *, optional: bool=True) -> 'CardFace|None':
    sense_deck = GetSenseDeck(player)
    if not sense_deck:
        return None

    faces = sense_deck.GetAll(from_top=True, include_removed=False)
    if optional:
        face = player.MayChooseFace(faces, effect, not_move=True)
    else:
        face = player.AskChooseFace(
            faces,
            effect,
            prompt="Choose a Sense upgrade to play",
        )
    if face:
        played = player.PlayCardsLikeInTurn(
            [face],
            effect,
            ignore_resources_cost=True,
            forced=True,
            if_not_play_discard_it=False,
        )
        return played[0] if played else None
    return None


def SenseCanAttachToEnemyOrScheme() -> 'Ability':
    return AbilityFactory.CanPlayThisUpgradeCard(
        CardFinder(card_type=Enemy|Scheme2)
    )


def SenseCompletionAbilities(operation: Callable[['Effect'], None]) -> Sequence['Ability']:
    def enemy_defeated(effect: 'Effect', message: 'Message.WhenUnitBeDefeated') -> None:
        operation(effect)

    def scheme_defeated(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        operation(effect)

    return [
        AbilityFactory.WhenUnitBeDefeated(
            AbilityType.Interrupt,
            "AttachedEnemy",
            enemy_defeated,
            has_defeating_player=True,
            conditions=[
                lambda effect, message:
                    message.defeating_player == effect.this.GetOwnerPlayer()
            ],
        ),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.Interrupt,
            "AttachedScheme",
            scheme_defeated,
            has_defeating_player=True,
            conditions=[
                lambda effect, message:
                    message.defeating_player == effect.this.GetOwnerPlayer()
            ],
        ),
    ]
