from . import *


def GetAbilities() -> Sequence['Ability']:
    def mission_team(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        selected_player = player.AskChooseOneText(Worlds.GetPlayers(effect))
        selected_player.DrawUp(1, effect)

    def cannot_discard(
        effect: 'Effect',
        message: 'Message.WhenCardWouldDiscard',
    ) -> None:
        message.SetBeInstead(effect)

    return [
        AbilityFactory.FirstPlayerControlThis(),
        AbilityFactory.WhenCardWouldDiscard(
            AbilityType.NonKeyword,
            "This",
            cannot_discard,
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            mission_team,
        ).AnyPlayerCanDoThis()
        .SetCostFunc(CostFunc.Exhaust("This")),
    ]
