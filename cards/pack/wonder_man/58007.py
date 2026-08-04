from . import *

# Wonder Fans


def GetAbilities() -> Sequence['Ability']:

    def wonder_fans(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        physiology = FindIonicPhysiology(effect)
        tuckable = GetEnergyCardsInDiscard(effect)
        can_tuck = bool(physiology and physiology.GetPlacedCardArea().GetSize() < 3 and tuckable)

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Tuck an energy event under Ionic Physiology",
                lambda targets: TuckUnderIonic(effect, targets),
                condition=can_tuck,
            ).SetTarget(tuckable),
            AbilityFactory.ForChoiceAbility(
                "Draw 1 card",
                lambda targets: player.DrawUp(1, effect),
            ),
        )

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.AlterEgoAction,
            wonder_fans,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
