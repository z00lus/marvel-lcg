from . import *
from cards.pack.mts.campaign import CampaignSetup

# All Hail King Loki

def GetAbilities() -> Sequence['Ability']:

    def all_hail_king_loki_before(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        villain = GetRandomSetAsideLokiVillain(effect)
        villain.Reveal(None, effect)

        Faces.MoveAllTo(GetSetAsideLokiVillains(effect), Worlds.GetScenario(effect).villain_deck, effect)

    def all_hail_king_loki(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        SetupCards.PutIntoPlay(
            effect,
            name="War in Asgard",
            card_type=SchemeSide2
        )

        face = GetInfinityStone(effect).GetTopCard()
        if face:
            face.Reveal(None, effect)

    return [
        *CampaignSetup(5),
        AbilityFactory.WhenCardSetupBeforePutSetupCards(
            all_hail_king_loki_before
        ),
        AbilityFactory.WhenCardSetup(
            "This",
            all_hail_king_loki
        ),
    ]
