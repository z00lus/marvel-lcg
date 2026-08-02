from . import *
from cards.pack.mut_gen.campaign import *

# The Sentinel Factory A

def GetAbilities() -> Sequence['Ability']:

    def the_sentinel_factory(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        player = Worlds.GetFirstPlayer(effect)

        SetupCards.PutIntoPlay(
            effect,
            for_player=player,
            name="Magneto",
            card_type=Ally,
            under_control=True,
        )

    return [
        *CampaignSetup(3),
        AbilityFactory.WhenCardSetup(
            "This",
            the_sentinel_factory
        ),
    ]
