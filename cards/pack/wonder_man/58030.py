from . import *

# Caught in the Crossfire

def GetAbilities() -> Sequence['Ability']:

    def caught_in_the_crossfire(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        this = effect.this.CastTo(Upgrade)
        Unused(this)

        this.DealDamage(effect.targets, 1, effect)


    return [
        AbilityFactory.CanPlayThisUpgradeCard(
            CardFinder(card_type=Minion, non_trait="ELITE")
        ),
        AbilityFactory.WhenUnitWouldAttack(
            AbilityType.Interrupt,
            Friend,
            caught_in_the_crossfire
        ).SetTarget("Attached"),
    ]
