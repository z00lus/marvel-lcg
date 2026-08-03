from . import *
from cards.pack.gmw.campaign import CampaignSetup

# The Missing Milano

def GetAbilities() -> Sequence['Ability']:

    def the_missing_milano(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        SetupCards.PutIntoPlay(
            effect,
            name=LIBRARY_LABYRINTH,
            card_type=Environment
        )

        villain = Worlds.FindVillain(effect)

        faces = SetupCards.SetAsideCards(
            effect,
            set_name="Ship Command",
        )
        assert villain
        GetShipCommand(effect).Create(effect, villain, type=DeckType.AsideDeck, has_discard_pile=False)
        GetShipCommand(effect).PushCards(faces, effect)

    return [
        AbilityFactory.WhenCardSetup(
            "This",
            the_missing_milano
        ),
        *CampaignSetup(3),
    ]
