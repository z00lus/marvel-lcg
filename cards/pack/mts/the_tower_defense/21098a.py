from . import *
from cards.pack.mts.campaign import CampaignSetup

# Under Siege

def GetAbilities() -> Sequence['Ability']:

    def under_siege_game_start(effect: 'Effect', message: 'Message.WhenGameBeginSetup') -> None:
        first_player = Worlds.GetFirstPlayer(effect)

        villains = Worlds.GetScenario(effect).villain_deck.FindCards(name="Proxima Midnight", card_type=Villain)
        villain = sorted(villains, key=lambda face: face.printed_stage)[0]
        villain.PutIntoPlay(first_player, effect)

        villains = Worlds.GetScenario(effect).villain_deck.FindCards(name="Corvus Glaive", card_type=Villain)
        villain = sorted(villains, key=lambda face: face.printed_stage)[0]
        villain.PutIntoPlay(first_player, effect)

        message.skip_put_villain_into_play = True

    def under_siege(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        first_player = Worlds.GetFirstPlayer(effect)

        scheme = Worlds.MainSchemesDeck(effect).Get()[0]
        assert scheme
        scheme.Reveal(first_player, effect)

    return [
        AbilityFactory.WhenGameBeginSetup(
            under_siege_game_start
        ),
        AbilityFactory.WhenCardSetup(
            "This",
            under_siege
        ),
        *CampaignSetup(2),
    ]
