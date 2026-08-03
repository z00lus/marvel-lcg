from . import *
from cards.pack.gmw.campaign import CampaignSetup

# The Grand Collection

def GetAbilities() -> Sequence['Ability']:

    def the_grand_collection(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        villain = Worlds.FindVillain(effect)
        assert villain
        GetTheCollection(effect).Create(effect, villain, type=DeckType.AsideDeck)

        def action(player: 'Player'):
            PutTopCardIntoTheCollection(player, effect)

        Players.ForEachPlayer(effect, action)

    return [
        AbilityFactory.WhenCardSetup(
            "This",
            the_grand_collection
        ),
        *CampaignSetup(2),
    ]
