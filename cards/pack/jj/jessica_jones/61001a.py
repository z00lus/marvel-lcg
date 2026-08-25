from . import *


def GetAbilities() -> Sequence['Ability']:

    def gather_evidence(effect: 'Effect', message: 'Message.AfterUnitUseBasicPower') -> None:
        PlaceEvidence(1, effect)

    return [
        AbilityFactory.AfterUnitUseBasicPower(
            AbilityType.Response,
            "You",
            gather_evidence,
            powers="Hero",
        ),
    ]
