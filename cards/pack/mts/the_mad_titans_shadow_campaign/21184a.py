from . import *


def GetAbilities() -> Sequence['Ability']:
    def hack_sanctuarys_computer(
        effect: 'Effect',
        message: 'Message.WhenSchemeBeDefeated',
    ) -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        for player in Worlds.GetPlayers(effect):
            card = Search.PlayerCard(
                effect,
                player,
                include_player_deck=True,
                include_discard_pile=True,
            )
            if card:
                player.GainCard(card, effect)
            if player.player_deck.GetSize():
                player.player_deck.Shuffle(effect)
        this.card.Flip(effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            hack_sanctuarys_computer,
        ),
    ]
