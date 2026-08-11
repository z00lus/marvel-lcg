from . import *
from cards.pack.sm.campaign import *

# Skies Over New York - 1A

def GetAbilities() -> Sequence['Ability']:

    def skies_over_new_york(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        first_player = Worlds.GetFirstPlayer(effect)

        for scheme in Worlds.MainSchemesDeck(effect).Get():
            scheme.PutIntoPlay(first_player, effect)
            if scheme.IsName("Midtown Manhattan"):
                Faces.PlaceCountersOn([scheme], 1, 'glider', effect)

        # Game rule will flip it, we don't need to call this
        # this.card.Flip(effect)

    def campaign(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
        # from game.card.factory import CardFactory
        this = effect.this
        Unused(this)

        card_ids = CampaignLog.GetList("Last Ones Standing: Victory for Scenario #4 - The Sinister Six", effect)
        card_ids2 = [{
            "27094": "27158",
            "27095": "27159",
            "27096": "27160",
            "27097": "27161",
            "27098": "27162",
            "27099": "27163",
        }[x] for x in card_ids]
        cards = CardFactory.GenerateCards(
            card_ids2,
            Worlds.AsideDeck(effect),
            effect.world,
        )
        Faces.ShuffleAllTo([x.face for x in cards], "EncounterDeck", effect)

    def campaign_expert(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
        this = effect.this
        this.PlaceThreatOnSchemes("EachMainScheme", "1*", effect)

    return [
        *CampaignSetup(5, campaign=campaign, campaign_expert=campaign_expert),
        AbilityFactory.WhenCardSetup(
            "This",
            skies_over_new_york
        )
    ]
