from . import *
from cards.pack.aoa.campaign_setup import *

# Dark Beast's Bogus Journey

def GetAbilities() -> Sequence['Ability']:

    def dark_beasts_bogus_journey(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        set_names: List[CardFace.SETNAMES] = ["Blue Moon", "Genosha", "Savage Land"]
        for set_name in set_names:
            SetupCards.SetAsideCards(
                effect,
                set_name=set_name,
            )

        if Worlds.IsExpert(effect):
            SetupCards.Reveal(
                effect,
                name="High-Tech Goggles",
                card_type=Attachment
            )

    return [
        AbilityFactory.WhenCardSetup(
            "This",
            dark_beasts_bogus_journey
        ),
        *CampaignSetup(4),
    ]
