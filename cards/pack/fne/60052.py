from . import *

# The Best Offense...


def GetAbilities() -> Sequence['Ability']:

    def use_defense(effect: 'Effect', message: 'Message.WhenUnitUseBasicPower') -> None:
        hero = effect.GetInitiator().GetHero()
        if message.power == "ATK":
            message.GainValue(hero.defense - hero.attack, effect)
        elif message.power == "THW":
            message.GainValue(hero.defense - hero.thwart, effect)

    return [
        *AbilityFactory.GiveKeywordToAttached(
            "You",
            defense=1,
        ),
        AbilityFactory.WhenUnitUseBasicPower(
            AbilityType.ForcedInterrupt,
            "You",
            use_defense,
            powers=["ATK", "THW"],
        ),
    ]
