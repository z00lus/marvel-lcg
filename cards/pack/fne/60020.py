from . import *

# * Cloak


def GetAbilities() -> Sequence['Ability']:

    def cloak(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        dagger = Search.PlayerCard(
            effect,
            player,
            include_player_deck=True,
            include_discard_pile=True,
            include_player_hand_cards=True,
            name="Dagger",
            card_type=Ally,
        )
        if dagger:
            dagger.PutIntoPlay(player, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            cloak,
        ).SetCostFunc(CostFunc.Exhaust("This")).SetCost(Cost("YY")),
    ]
