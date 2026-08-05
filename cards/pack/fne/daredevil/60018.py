from . import *

# * The Man Without Fear


def GetAbilities() -> Sequence['Ability']:

    def the_man_without_fear(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Choose and play a Sense upgrade without paying its cost",
                lambda targets: ChooseAndPlaySense(player, effect, optional=False),
            ),
            AbilityFactory.ForChoiceAbility(
                "Ready Daredevil",
                lambda targets: Faces.ReadyAll([player.GetHero()], effect),
            ),
        )

    return [
        AbilityFactory.CanPlayThisUpgradeCard("YourIdentity"),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            the_man_without_fear,
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetCostFunc(CostFunc.DealDamage(1, "YourHero")),
    ]
