from . import *


def GetAbilities() -> Sequence['Ability']:
    def team_assembled(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Environment)
        if not Faces.RemoveCountersOn([this], 1, 'assembly', effect):
            return

        def search_for_ally(player: 'Player') -> None:
            def search(targets: Sequence['CardFace']) -> None:
                ally = Search.PlayerCard(
                    effect,
                    player,
                    include_player_deck=True,
                    include_discard_pile=True,
                    card_type=Ally,
                    cost_less_than=3,
                )
                if ally:
                    ally.PutIntoPlay(player, effect)

            player.MayChooseOneAbility(
                effect,
                AbilityFactory.ForChoiceAbility(
                    "Search their deck and discard pile for an ally with a printed cost of 3 or less and put it into play",
                    search,
                ),
            )

        Players.ForEachPlayer(effect, search_for_ally)

    return [
        AbilityFactory.ThisEnterPlayWithCounters(1, 'assembly'),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            team_assembled,
        ).AnyPlayerCanDoThis()
        .SetTarget("This", has_counter='assembly'),
    ]
