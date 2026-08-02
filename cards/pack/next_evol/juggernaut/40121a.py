from . import *
from cards.pack.next_evol.campaign import *

# The Unstoppable Juggernaut

def GetAbilities() -> Sequence['Ability']:

    def the_unstoppable_juggernaut(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        villain = Worlds.FindCardOnField(
            effect,
            name="Juggernaut",
            card_type=Villain
        )
        if villain:
            SetupCards.AttachTo(
                effect,
                name="Juggernaut's Helmet",
                attach_to=villain
            )

        # We don't need this because "40130" has Setup keyword
        # Add this will cause deck shuffle
        # We need this for compatibility
        if not Worlds.FindCardOnField(
            effect,
            name="Hope Summers",
        ):
            player = Worlds.GetFirstPlayer(effect)
            SetupCards.PutIntoPlay(
                effect,
                for_player=player,
                name="Hope Summers",
                under_control=True,
            )

    return [
        *CampaignSetup(3),
        AbilityFactory.WhenCardSetup(
            "This",
            the_unstoppable_juggernaut
        ),
    ]
