from . import *
from cards.pack.next_evol.campaign import *

# Uncontrollable Power

def GetAbilities() -> Sequence['Ability']:

    def uncontrollable_power(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        if not Worlds.FindCardOnField(
            effect,
            name="Hope Summers",
        ):
            player = Worlds.GetFirstPlayer(effect)
            SetupCards.PutIntoPlay(
                effect,
                name="Hope Summers",
                for_player=player,
                under_control=True,
            )

        SetupCards.Reveal(
            effect,
            name="Stryfe's Grasp",
        )

    return [
        *CampaignSetup(5),
        AbilityFactory.WhenCardSetup(
            "This",
            uncontrollable_power
        ),
    ]
