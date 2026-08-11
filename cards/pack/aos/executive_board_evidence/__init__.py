from cards.pack import *

def EvidenceOpportunity(card_class: "ClassCard.CARD_CLASS"):
    return EvidenceInternal(card_class, Support)

def EvidenceMotive(card_class: "ClassCard.CARD_CLASS"):
    return EvidenceInternal(card_class, Upgrade)

def EvidenceMeans(card_class: "ClassCard.CARD_CLASS"):
    return EvidenceInternal(card_class, Ally)

def EvidenceInternal(card_class: "ClassCard.CARD_CLASS", card_type: Type[CardFace]):

    def medical_records(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(Evidence)
        Unused(this)

        collection_choices: Set[str] = set()

        def action_a(player: 'Player'):
            def search(targets: Sequence['CardFace']):
                Faces.PlaceCountersOn(targets, 1, 'secret', effect)
                face = Search.Collection(
                    effect,
                    player,
                    card_classes=[card_class],
                    card_type=card_type,
                    check_fn=lambda paper:
                        paper.card_id not in collection_choices,
                )
                if face:
                    collection_choices.add(face.paper.card_id)
                    Faces.ShuffleAllTo([face], player.player_deck, effect)

            player.MayChooseOneAbility(
                effect,
                AbilityFactory.ForChoiceAbility(
                    f"Add 1 secret counter to a [[Board Member]] environment to search their collection for a different {card_class} {card_type} and shuffle it into their deck",
                    search,
                ).SetTarget(Environment, trait="BOARD MEMBER")
            )
        Players.ForEachPlayer(effect, action_a)

        def action_b(player: 'Player'):
            def search(targets: Sequence['CardFace']):
                this.PlaceThreatOnSchemes(targets, 1, effect)
                face = Search.PlayerCard(
                    effect,
                    player,
                    include_player_deck=True,
                    card_type=card_type,
                    card_class=card_class
                )
                if face:
                    Faces.AddToHand([face], player, effect)

            player.MayChooseOneAbility(
                effect,
                AbilityFactory.ForChoiceAbility(
                    f"Add 1 threat to the main scheme to search their deck for an {card_class} {card_type} and add it to their hand.",
                    search,
                ).SetTarget(MainScheme, can_place_threat=True)
            )

        Players.ForEachPlayer(effect, action_b)

    return AbilityFactory.WhenCardSetup(
        "This",
        medical_records
    ).NoOutOfPlayLimit()
