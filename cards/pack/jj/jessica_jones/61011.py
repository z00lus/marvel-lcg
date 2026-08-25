from . import *


def GetAbilities() -> Sequence['Ability']:

    def leather_jacket(effect: 'Effect', message: 'Message.AfterUnitDefendEnd') -> None:
        PlaceEvidence(1, effect)

    return [
        *AbilityFactory.GiveKeywordToInPlayWhenApplyThis(
            "You",
            defense=2,
        ),
        AbilityFactory.AfterUnitDefendEnd(
            AbilityType.Response,
            "You",
            leather_jacket,
        ),
    ]
