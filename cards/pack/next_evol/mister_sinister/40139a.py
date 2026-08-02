from . import *
from cards.pack.next_evol.campaign import *

# Sinister Intent

def GetAbilities() -> Sequence['Ability']:

    def sinister_intent(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        set_names: List[CardFace.SETNAMES] = ["Flight", "Super Strength", "Telepathy"]
        for set_name in set_names:
            SetupCards.SetAsideCards(
                effect,
                set_name=set_name,
            )

        # See "40121a"
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

    return [
        *CampaignSetup(4),
        AbilityFactory.WhenCardSetup(
            "This",
            sinister_intent,
        ),
    ]
