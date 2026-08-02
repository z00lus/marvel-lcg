from . import *
from cards.pack.mut_gen.campaign import *

# Asteroid M A

def GetAbilities() -> Sequence['Ability']:

    def asteroid_m(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        SetupCards.Reveal(
            effect,
            name="Boarding Party",
            card_type=SchemeSide2
        )

    return [
        *CampaignSetup(5),
        AbilityFactory.WhenCardSetup(
            "This",
            asteroid_m
        ),
    ]
