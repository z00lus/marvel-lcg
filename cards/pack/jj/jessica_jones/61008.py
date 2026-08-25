from . import *


def GetAbilities() -> Sequence['Ability']:

    def calling_in_favors(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        ally = Search.PlayerCard(
            effect,
            player,
            include_player_deck=True,
            card_type=Ally,
            may=False,
        )
        if ally:
            player.PlayCardsLikeInTurn([ally], effect, update_resources_cost=-2)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.AlterEgoAction,
            calling_in_favors,
        ).SetCostFunc(CostFunc.Counter(CardFinder(name="Alias Investigations"), 2, EVIDENCE_COUNTER))
        .SetCostFunc(CostFunc.Exhaust("This")),
    ]
