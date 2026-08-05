from . import *

# * Karen Page


def GetAbilities() -> Sequence['Ability']:

    def karen_page(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        Faces.ShuffleAllTo(effect.targets, player.player_deck, effect)
        if player.IsAlterEgo():
            player.DrawUp(1, effect)

    return [
        AbilityFactory.CanPlayThisSupportCard(),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            karen_page,
        ).SetCostFunc(CostFunc.Exhaust("This")).SetTarget(
            CardFinder(set_name="Daredevil"),
            from_where=["YourDiscardPile"],
        ),
    ]
