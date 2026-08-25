from . import *


def GetAbilities() -> Sequence['Ability']:

    def circumstantial_evidence(effect: 'Effect', message: 'Message.AfterUnitBeDefeated') -> None:
        PlaceEvidence(1, effect)

    return [
        AbilityFactory.AfterUnitBeDefeated(
            AbilityType.Response,
            Enemy,
            circumstantial_evidence,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
