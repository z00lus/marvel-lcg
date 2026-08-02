from . import *


def GetAbilities() -> Sequence['Ability']:
    def geared_up(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Environment)
        if not Faces.RemoveCountersOn([this], 1, 'pouch', effect):
            return

        for player in Worlds.GetPlayers(effect):
            CardFactory.GenerateCard("40196", player.player_deck, effect.world)
            player.player_deck.Shuffle(effect)

    return [
        AbilityFactory.ThisEnterPlayWithCounters(1, 'pouch'),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            geared_up,
        ).AnyPlayerCanDoThis()
        .SetTarget("This", has_counter='pouch'),
    ]
