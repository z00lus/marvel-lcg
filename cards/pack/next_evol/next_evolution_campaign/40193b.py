from . import *


def GetAbilities() -> Sequence['Ability']:
    def mission_prepped(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Environment)
        if not Faces.RemoveCountersOn([this], 1, 'prep', effect):
            return

        for player in Worlds.GetPlayers(effect):
            upgrade = Search.PlayerCard(
                effect,
                player,
                include_player_deck=True,
                include_discard_pile=True,
                card_type=Upgrade,
                cost_less_than=2,
            )
            if upgrade:
                upgrade.PutIntoPlay(player, effect)

    return [
        AbilityFactory.ThisEnterPlayWithCounters(1, 'prep'),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            mission_prepped,
        ).AnyPlayerCanDoThis()
        .SetTarget("This", has_counter='prep'),
    ]
