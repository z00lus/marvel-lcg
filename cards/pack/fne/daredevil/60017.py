from . import *

# * Daredevil's Billy Club


def GetAbilities() -> Sequence['Ability']:

    def billy_club(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Upgrade)
        player = effect.GetInitiator()
        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Deal 1 damage to an enemy",
                lambda targets: this.DealDamage(targets, 1, effect),
            ).SetLabel("attack").SetTarget(Enemy),
            AbilityFactory.ForChoiceAbility(
                "Daredevil gains Aerial until the end of the round",
                lambda targets: player.GetHero().GainUntilRoundEnd(effect, trait="AERIAL"),
            ),
        )

    return [
        AbilityFactory.CanPlayThisUpgradeCard("YourIdentity"),
        *AbilityFactory.GiveKeywordToAttached(
            CardFinder(name="Daredevil"),
            attack=1,
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            billy_club,
        ).SetCostFunc(CostFunc.ReturnToHand("This", to_who="Initiator")),
    ]
