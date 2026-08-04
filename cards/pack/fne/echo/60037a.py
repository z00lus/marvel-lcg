from . import *

# * Echo


def GetAbilities() -> Sequence['Ability']:

    def has_photographic_reflexes(effect: 'Effect') -> bool:
        initiator = effect.GetInitiator()
        return initiator.IsHero() and bool(
            initiator.hand_cards.FindCards(name="Photographic Reflexes", card_type=Event)
        )

    def watch_and_learn(effect: 'Effect', message: 'Message.AfterPlayerPlayedCard') -> None:
        this = effect.this.CastTo(Hero)
        played_event = message.played_face

        # Events copied with Photographic Reflexes came from this area and cannot
        # trigger Watch and Learn again.
        if message.from_area == this.GetPlacedCardArea():
            return

        if played_event.card.area.flags.is_discards:
            this.TuckCardUnderHere(played_event, effect)

        tucked_cards = this.GetPlacedCardArea().GetAll()
        excess = len(tucked_cards) - 3
        if excess > 0:
            this.GetControlByPlayer().AskDiscardFaces(tucked_cards, (excess, excess), effect)

    def spend_photographic_reflexes(effect: 'Effect', message: 'Message.WhenPlayerWouldPlayCard') -> None:
        initiator = effect.GetInitiator()
        reflexes = initiator.hand_cards.FindCards(
            name="Photographic Reflexes",
            card_type=Event,
        )
        chosen = initiator.AskChooseFace(reflexes, effect)
        if chosen:
            Faces.DiscardAll([chosen], effect)

    tucked_event = CardFinder(card_type=Event)

    return [
        AbilityFactory.AfterPlayerPlayedCard(
            AbilityType.Response,
            "AnyPlayer",
            tucked_event,
            watch_and_learn,
            conditions=[
                lambda effect, message:
                    IsAspectOrBasicEvent(message.played_face) and
                    message.from_area != effect.this.GetPlacedCardArea()
            ],
        ).SetName("Watch and Learn"),
        *AbilityFactory.YouMayPlayCardLikeInHand(
            AbilityType.NonKeyword,
            tucked_event,
            from_where="ThisPlacedCard",
            conditions=[
                lambda effect, message: has_photographic_reflexes(effect)
            ],
        ),
        AbilityFactory.ReduceCostToPlayFaceWhen(
            tucked_event,
            2,
            "You",
            conditions=[
                lambda effect, message:
                    message.check_effect.this.card.area == effect.this.GetPlacedCardArea() and
                    has_photographic_reflexes(effect)
            ],
        ),
        AbilityFactory.WhenPlayerWouldPlayCard(
            AbilityType.NonKeyword,
            "You",
            tucked_event,
            spend_photographic_reflexes,
            conditions=[
                lambda effect, message:
                    message.from_area == effect.this.GetPlacedCardArea() and
                    has_photographic_reflexes(effect)
            ],
        ),
    ]
