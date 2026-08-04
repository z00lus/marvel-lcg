from . import *

# Cameo

def GetAbilities() -> Sequence['Ability']:

    def cameo(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(Support)
        Unused(this)

        initiator = effect.GetInitiator()
        identity_sets = {
            player.GetIdentity().paper.set_name
            for player in Worlds.GetPlayers(effect)
        }

        ally = Search.Collection(
            effect,
            initiator,
            card_type=Ally,
            card_class="IdentitySpecific",
            check_fn=lambda paper: paper.set_name not in identity_sets,
        )

        if ally:
            Faces.ShuffleAllTo([ally], initiator.player_deck, effect)
        
        initiator.DiscardHandCards((2, 2), effect)
        Faces.RemoveAllFromGame([this], effect)


    return [
        AbilityFactory.WhenCardSetup(
            "This",
            cameo
        ),
    ]
