from . import *
from cards.pack.mts.campaign import CampaignSetup

# Odin's Torment

def GetAbilities() -> Sequence['Ability']:

    def odins_torment(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        SetupCards.AttachTo(
            effect,
            this,
            name="Odin",
            card_type=Ally,
            flip_to_trait="CAPTIVE",
        )

        SetupCards.Reveal(
            effect,
            name="Gnipahellir"
        )
        SetupCards.Reveal(
            effect,
            name="Garm"
        )

        # Set Gjallerbru, Skurge, Hall of Nastrond, and Nidhogg aside, out of play

    return [
        *CampaignSetup(4),
        AbilityFactory.WhenCardSetup(
            "This",
            odins_torment
        ),
    ]
