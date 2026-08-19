from . import *


def GetAbilities() -> Sequence['Ability']:
    def place_civilian(effect: 'Effect', player: 'Player') -> bool:
        disaster = ChooseDisaster(player, effect)
        if not disaster:
            return False
        Faces.PlaceCountersOn([disaster], 1, 'civilian', effect)
        return True

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        if place_civilian(effect, player):
            return
        disaster = Search.EncounterCard(
            effect,
            player,
            include_discard_pile=True,
            trait="DISASTER",
            card_type=Environment,
        )
        if disaster:
            disaster.Reveal(player, effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        place_civilian(effect, message.GetToPlayer())

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
