from . import *


def GetAbilities() -> Sequence['Ability']:
    def attacked(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> None:
        this = effect.this.CastTo(Minion)
        face = Worlds.DiscardEncounterTopCard(effect)
        if face:
            damage = FacesCounter.CountTotalBoostIcons([face])
            if damage:
                message.attacker.TakeDamage(this, damage, effect)

    return [
        AbilityFactory.WhenUnitWouldAttackUnit(
            AbilityType.ForcedInterrupt,
            "YouControlCharacter",
            "This",
            attacked,
        ).SetCostFunc(CostFunc.Counter(ELECTRIC_CHARGE, 1, 'charge')),
    ]
