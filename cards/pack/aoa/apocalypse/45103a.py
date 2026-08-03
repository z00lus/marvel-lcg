from . import *
from cards.pack.aoa.campaign_setup import *

# The Age of Apocalypse

def GetAbilities() -> Sequence['Ability']:

    def the_age_of_apocalypse(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        SetupCards.Reveal(
            effect,
            name="Heart of the Empire",
            card_type=SchemeSide2
        )

        SetupCards.SetAsideCards(
            effect,
            trait="PRELATE",
            card_type=Minion
        )
        player = Worlds.GetFirstPlayer(effect)
        RevealRandomSetasidePRELATEMinion(player, effect)


    return [
        AbilityFactory.WhenCardSetup(
            "This",
            the_age_of_apocalypse
        ),
        *CampaignSetup(3),
    ]
