from . import *


def GetAbilities() -> Sequence['Ability']:

    def remove_ally(targets: Sequence['CardFace'], effect: 'Effect') -> bool:
        return Faces.RemoveAllFromGame(targets, effect) == list(targets)

    def confuse_identity(targets: Sequence['CardFace'], effect: 'Effect') -> bool:
        return bool(Faces.GiveStatus(targets, "Confused", effect))

    return [
        AbilityFactory.AdditionalCostToChangeForm(
            "You",
            CostFunc.Discard("YourHandCards"),
        ),
        AbilityFactory.PlayerActionToRemoveThisFromGame(
            AbilityType.AlterEgoAction,
        ).SetName("Remove an ally you control from the game")
        .SetCostFunc(CostFunc.Custom(
            Select.From("YourAlly", range=(1, 1)),
            remove_ally,
        )),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.AlterEgoAction,
        ).SetName("Confuse your identity")
        .SetCostFunc(CostFunc.Custom(
            Select.From("YourIdentity", finder=CardFinder(canbe_confused=True)),
            confuse_identity,
        )),
    ]
