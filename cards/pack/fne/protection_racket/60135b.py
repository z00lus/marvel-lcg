from . import *


def GetAbilities() -> Sequence['Ability']:
    def excess_damage(effect: 'Effect', message: 'Message.AfterUnitDefeatedUnit') -> None:
        PlaceThreatHere(effect, message.excess_damage)

    def valid_target(effect: 'Effect', message: 'Message.AfterUnitDefeatedUnit') -> bool:
        if Ally.IsType(message.target):
            return True
        return Worlds.IsExpert(effect) and Minion.IsType(message.target)

    return [
        AbilityFactory.AfterUnitDealExcessDamage(
            AbilityType.ForcedInterrupt,
            Unit2,
            excess_damage,
            conditions=[valid_target],
        ),
    ]
