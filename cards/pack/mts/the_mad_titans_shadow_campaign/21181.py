from . import *


def GetAbilities() -> Sequence['Ability']:
    def security_breach_revealed(
        effect: 'Effect',
        message: 'Message.WhenCardRevealed',
    ) -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        cards = [
            card
            for player in Worlds.GetPlayers(effect)
            for card in player.GetRandomHandCards(1)
        ]
        this.PlaceCardHere(cards, False, effect)

    def security_breach_defeated(
        effect: 'Effect',
        message: 'Message.WhenSchemeBeDefeated',
    ) -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        Faces.ReturnToHand(this.GetPlacedCardArea().Get(True), "Owner", effect)

    return [
        AbilityFactory.WhenThisRevealed(None, security_breach_revealed),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            security_breach_defeated,
        ),
    ]
