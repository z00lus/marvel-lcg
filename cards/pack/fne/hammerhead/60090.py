from . import *


def GetAbilities() -> Sequence['Ability']:
    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        Faces.GiveStatus([message.activating_enemy], "Tough", effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(HAMMERHEAD),
        *AbilityFactory.GiveKeywordToAttached(Villain, stalwart=1),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.HeroAction,
        ).SetCost(Cost("YBR")),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
