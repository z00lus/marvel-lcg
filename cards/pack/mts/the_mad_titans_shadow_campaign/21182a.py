from . import *


def GetAbilities() -> Sequence['Ability']:
    def save_the_shawarma_place(
        effect: 'Effect',
        message: 'Message.WhenSchemeBeDefeated',
    ) -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        for player in Worlds.GetPlayers(effect):
            CardFactory.GenerateCard("21183", player.player_deck, effect.world)
            player.player_deck.Shuffle(effect)
        this.card.Flip(effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            save_the_shawarma_place,
        ),
    ]
