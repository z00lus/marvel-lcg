from . import *
from cards.pack.gmw.campaign import CampaignSetup

# The Art of Evasion

def GetAbilities() -> Sequence['Ability']:

    def the_art_of_evasion(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        SetupCards.PutIntoPlay(
            effect,
            name="Nebula's Ship",
            card_type=Environment
        )

        # Search.SearchForCards(
        #     effect,
        #     world.GetSetAsideAreaCards(),
        #     lambda face: face.PutIntoPlay(player, effect),
        #     name="Power Stone",
        #     card_type=Environment,
        # )

        nebula = Worlds.FindVillain(effect)

        faces = Worlds.DiscardEncounterCards("2*", effect)
        for face in faces:
            if Attachment.IsType(face) and face.HasTrait("TECHNIQUE") and nebula:
                face.AttachTo2(nebula, effect)


    return [
        AbilityFactory.WhenCardSetup(
            "This",
            the_art_of_evasion
        ),
        *CampaignSetup(4),
    ]
