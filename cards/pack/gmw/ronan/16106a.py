from . import *
from cards.pack.gmw.campaign import CampaignSetup

# Interception Imminent

def GetAbilities() -> Sequence['Ability']:

    def interception_imminent(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        first_player = Worlds.GetFirstPlayer(effect)
        villain = Worlds.FindVillain(effect)

        SetupCards.PutIntoPlay(
            effect,
            name="Kree Command Ship",
            card_type=Environment
        )
        if villain:
            SetupCards.AttachTo(
                effect,
                attach_to=villain,
                name="Universal Weapon",
                card_type=Attachment
            )

        face = GetPowerStone(effect)
        if face:
            face.AttachTo2(first_player.GetIdentity(), effect)


    return [
        AbilityFactory.WhenCardSetup(
            "This",
            interception_imminent,
        ),
        *CampaignSetup(5),
    ]
