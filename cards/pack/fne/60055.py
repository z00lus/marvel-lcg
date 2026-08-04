from . import *

# See No Evil, Hear No Evil


def GetAbilities() -> Sequence['Ability']:

    def choose_effect(effect: 'Effect') -> None:
        this = effect.this.CastTo(Event)
        initiator = effect.GetInitiator()
        initiator.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Deal 3 damage to an enemy",
                lambda targets: this.DealDamage(targets, 3, effect),
            ).SetLabel("attack").SetTarget(Enemy),
            AbilityFactory.ForChoiceAbility(
                "Remove 3 threat from a scheme",
                lambda targets: this.RemoveThreatFromSchemes(targets, 3, effect),
            ).SetLabel("thwart").SetTarget(Scheme2),
        )

    def see_no_evil_hear_no_evil(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        choose_effect(effect)
        choose_effect(effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            see_no_evil_hear_no_evil,
        ).SetPlay().SetLabel("attack", "thwart")
        .SetTarget("TeamUp"),
    ]
