from . import *
from cards.pack.mut_gen.campaign import *

# Night of the Sentinels A

def GetAbilities() -> Sequence['Ability']:

    def night_of_the_sentinels(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        # Set each [[Captive]] ally aside

        SetupCards.Reveal(
            effect,
            name="Operation Zero Tolerance",
            card_type=SchemeSide2
        )
        SetupCards.Reveal(
            effect,
            name="Mutants at the Mall",
            card_type=SchemeSide2
        )

    return [
        *CampaignSetup(2),
        AbilityFactory.WhenCardSetup(
            "This",
            night_of_the_sentinels
        ),
    ]
