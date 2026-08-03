from . import *
from cards.pack.aoa.campaign_setup import *

# The Horsemen of Apocalypse

def GetAbilities() -> Sequence['Ability']:

    def the_horsemen_of_apocalypse(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        villains = Worlds.AsideDeck(effect).FindCards(
            trait="HORSEMEN",
            card_type=Villain
        )
        Rand.Shuffle(villains, effect)
        for villain in villains:
            villain.Reveal(None, effect)

        villains[0].SetActive(effect)

        def action(player: 'Player'):
            face = Worlds.GetEncounterDeck(effect).FindCard(
                set_name="Four Horsemen",
                card_type=SchemeSide2
            )
            if face:
                face.Reveal(player, effect)

        Players.ForEachPlayer(effect, action)

    return [
        AbilityFactory.WhenCardSetup(
            "This",
            the_horsemen_of_apocalypse
        ),
        *CampaignSetup(2),
    ]
