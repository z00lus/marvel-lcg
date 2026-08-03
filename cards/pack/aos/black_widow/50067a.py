from . import *
from cards.pack.aos.campaign import CampaignSetup

# The Widow's Web

def GetAbilities() -> Sequence['Ability']:

    def the_widows_web(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        def action(player: 'Player'):
            face = Search.EncounterCard(
                effect,
                player,
                include_discard_pile=False,
                card_type=Minion,
            )
            if face:
                face.PutIntoPlay(player, effect)

        Players.ForEachPlayer(
            effect,
            action,
        )

    return [
        AbilityFactory.WhenCardSetup(
            "This",
            the_widows_web
        ),
        *CampaignSetup(1),
    ]
