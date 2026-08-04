from . import *

# Impact-Dampening Suit

def GetAbilities() -> Sequence['Ability']:

    def impact_dampening_suit(effect: 'Effect', message: 'Message.WhenPhaseBegin') -> None:
        this = effect.this.CastTo(Upgrade)
        Unused(this)

        this.effect.RegisterTemp(
            AbilityFactory.ReduceCharacterTakeDamageBy(
                "YourHero",
                1,
                from_each_attack=True,
                who_deal_damage=Enemy
            ),
            unregister_after_exec=False,
            until_phase_end=True
        )


    return [
        *AbilityFactory.GiveKeywordToAttached(
            "You",
            health=2
        ),
        AbilityFactory.WhenPhaseBegin(
            AbilityType.HeroInterrupt,
            "Villain",
            impact_dampening_suit
        ).SetCost(Cost("1")),
    ]
