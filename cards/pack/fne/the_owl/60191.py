from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            NON_AERIAL_ENEMY,
            if_cannot_gain_surge=True,
        ),
        *AbilityFactory.GiveKeywordToAttached(
            Enemy,
            trait="AERIAL",
        ),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.HeroAction,
        ).SetCostFunc(CostFunc.Discard(
            "YourHandCards",
            trait="ATTACK",
            card_type=Event,
        )),
    ]
