from cards.pack import *


def CampaignPlayerSideScheme() -> 'Ability':
    def flip_to_environment(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        this = effect.this.CastTo(PlayerSideScheme)
        this.card.Flip(effect)
        this.card.face.PutIntoPlay(Worlds.GetFirstPlayer(effect), effect)

    return AbilityFactory.WhenSchemeBeDefeated(
        AbilityType.WhenDefeated,
        "This",
        flip_to_environment,
    )
