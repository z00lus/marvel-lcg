from cards.pack import *


NON_AERIAL_ENEMY = CardFinder(card_type=Enemy, non_trait="AERIAL")


def PiercingAttackAbility(*, ranged: bool=False) -> 'Ability':
    def attack(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        message.GainPiercing(effect)
        if ranged:
            message.GainRanged(effect)

    return AbilityFactory.WhenUnitWouldAttack(
        AbilityType.ForcedInterrupt,
        "This",
        attack,
    )
