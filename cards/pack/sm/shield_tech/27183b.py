from . import *

# Impact-Dampening Suit

def GetAbilities() -> Sequence['Ability']:

    def impact_dampening_suit(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        this = effect.this.CastTo(Upgrade)
        Unused(this)

        message.PreventDamage(1, effect)


    return [
        *AbilityFactory.GiveKeywordToAttached(
            "You",
            health=3
        ),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.HeroInterrupt,
            "YourHero",
            impact_dampening_suit,
            is_from_attack=True,
            who_deal_damage=Enemy,
        ).SetCostFunc(CostFunc.DiscardDeckTopCards("YourDeck", 1)),
    ]

