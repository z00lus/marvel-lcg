from . import *

# * Wonder Man


def GetAbilities() -> Sequence['Ability']:

    def power_recycling(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> None:
        physiology = FindIonicPhysiology(effect)
        if physiology:
            Faces.DiscardAll(physiology.GetPlacedCardArea().GetAll(), effect)

    return [
        AbilityFactory.AfterUnitMakeBasicAttack(
            AbilityType.ForcedResponse,
            "You",
            power_recycling,
        ),
    ]
