from . import *

# * Blindspot


def GetAbilities() -> Sequence['Ability']:

    def blindspot(effect: 'Effect', message: 'Message.AfterUnitUseBasicPower') -> None:
        Faces.GiveStatus(effect.targets, "Confused", effect)

    return [
        AbilityFactory.AfterUnitUseBasicPower(
            AbilityType.Response,
            "This",
            blindspot,
            powers=["THW"],
        ).SetTarget(
            CardFinder(card_type=Enemy, with_attach=Upgrade, canbe_confused=True)
        ),
    ]
