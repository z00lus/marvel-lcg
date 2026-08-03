from . import *
from cards.pack.aos.campaign import CampaignSetup

# Infiltrate A.I.M. Island Embassy

def GetAbilities() -> Sequence['Ability']:

    def infiltrate_aim_island_embassy(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        SetupCards.SetAsideCards(
            effect,
            name="Rescued Captive",
            card_type=Ally
        )

        env = SetupCards.PutIntoPlay(
            effect,
            name="Alert Level",
            card_type=Environment,
            flip_to_trait="LOW"
        )

        if Worlds.IsExpert(effect) and env:
            Faces.PlaceTokensOn([env], "2*", 'threat', effect)


    return [
        AbilityFactory.WhenCardSetup(
            "This",
            infiltrate_aim_island_embassy
        ),
        *CampaignSetup(2),
    ]
