from . import *


# Find the Prisoners

def GetAbilities() -> Sequence['Ability']:
    def find_the_prisoners_revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(EncounterSideScheme)

        def tuck_ally(player: 'Player') -> None:
            ally = Search.PlayerCard(
                effect,
                player,
                include_player_deck=True,
                card_type=Ally,
            )
            if ally:
                this.PlaceCardHere(ally, False, effect)

        Players.ForEachPlayer(effect, tuck_ally)

    def find_the_prisoners_defeated(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        ShuffleRandomFuturePastCardIntoEncounterDeck(effect)
        this.card.Flip(effect)
        this.card.face.PutIntoPlay(Worlds.GetFirstPlayer(effect), effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            find_the_prisoners_revealed,
        ),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            find_the_prisoners_defeated,
        ),
    ]
