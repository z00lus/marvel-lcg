from . import *


def GetAbilities() -> Sequence['Ability']:
    def mission_team(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Reduce the cost of the next ally played to the mission this phase by 2",
                lambda targets:
                    ReduceNextMissionAllyCost(player, effect),
            ),
            AbilityFactory.ForChoiceAbility(
                "Make a mission attempt",
                lambda targets:
                    MakeMissionAttempt(player, effect),
                condition=bool(GetMissionAllies(effect)),
            ),
        )

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
        AbilityFactory.WhenPlayerPhaseEnd(
            AbilityType.Temp0,
            lambda effect, message:
                ClearMissionAllyFlags(effect),
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            mission_team,
        ).AnyPlayerCanDoThis()
        .SetCostFunc(CostFunc.Exhaust("This")),
    ]
