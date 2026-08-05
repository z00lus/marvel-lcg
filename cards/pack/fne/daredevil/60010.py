from . import *

# Living Lie Detector


def GetAbilities() -> Sequence['Ability']:

    def living_lie_detector(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        target = effect.targets[0]
        upgrades = GetAttachedUpgradeCount(target)
        additional = effect.GetInitiator().AskChooseOneText(
            list(range(upgrades + 1)),
            [f"Remove {value} additional threat" for value in range(upgrades + 1)],
        )
        this.RemoveThreatFromSchemes([target], 2 + additional, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            living_lie_detector,
        ).SetPlay().SetLabel("thwart").SetTarget(Scheme2),
    ]
