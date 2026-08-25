from . import *


def SuggestionAbilities(resource: 'Resources.RBYG') -> Sequence['Ability']:

    def suggestion(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        playable = CardFinder(
            has_printed_res=resource,
            canbe_play=True,
        ).Checks(player.hand_cards.Get(), effect)

        def play_or_place_threat(targets: Sequence['CardFace']) -> None:
            played = player.PlayCardsLikeInTurn(
                list(targets),
                effect,
                if_not_play_discard_it=False,
            )
            if not played:
                effect.this.PlaceThreatOnSchemes("MainScheme", 2, effect)

        choices = [
            AbilityFactory.ForChoiceAbility(
                "Add 2 threat to the main scheme",
                lambda targets: effect.this.PlaceThreatOnSchemes("MainScheme", 2, effect),
            ),
        ]
        if playable:
            choices.insert(
                0,
                AbilityFactory.ForChoiceAbility(
                    f"Play a card with a printed {resource} resource icon",
                    play_or_place_threat,
                ).SetTarget(playable, finder=CardFinder(canbe_play=True), range=(1, 1)),
            )
        player.ChooseAbilities(effect, *choices)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.ForcedAction,
            suggestion,
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetCostFunc(CostFunc.Counter("This", 1, PHEROMONE_COUNTER)),
    ]
