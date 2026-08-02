from . import *
from cards.pack.mut_gen.campaign import *

# Stalked by Sabretooth 1A

def GetAbilities() -> Sequence['Ability']:

    def stalked_by_sabretooth_1a(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        scheme = SetupCards.PutIntoPlay(
            effect,
            name="Find the Senator",
            card_type=SchemeSide2
        )
        if scheme:
            SetupCards.AttachTo(
                effect,
                scheme,
                finder=ROBERT_KELLY_FINDER,
                card_type=Ally
            )

    return [
        *CampaignSetup(1),
        AbilityFactory.WhenCardSetup(
            "This",
            stalked_by_sabretooth_1a
        ),
    ]
