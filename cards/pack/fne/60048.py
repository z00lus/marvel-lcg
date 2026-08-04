from . import *

# Army of One


def GetAbilities() -> Sequence['Ability']:

    def army_of_one(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        Faces.ReadyAll([effect.GetInitiator().GetHero()], effect)

    return [
        AbilityFactory.IncreaseResourceCostToPlay(
            "This",
            lambda effect: len(effect.GetInitiator().GetControlAllies()),
            "You",
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            army_of_one,
        ).SetPlay().SetLabel(),
    ]
