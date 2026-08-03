from . import *
from cards.pack.aoa.campaign_setup import *

# En Sabah Nur's Pyramid

def GetAbilities() -> Sequence['Ability']:

    def en_sabah_nurs_pyramid(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        def action(player: 'Player'):
            player.DealEncounterCards(1, effect)

        Players.ForEachPlayer(effect, action)

    return [
        AbilityFactory.WhenCardSetup(
            "This",
            en_sabah_nurs_pyramid
        ),
        *CampaignSetup(5),
    ]
