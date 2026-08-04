from . import *

# * Swordsman


def GetAbilities() -> Sequence['Ability']:

    def swordsman_attack(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> None:
        message.GainPiercing(effect)

    def swordsman_defend(effect: 'Effect', message: 'Message.WhenBoostCardTurnedFaceUp') -> None:
        message.would_atk_message.DeclareDefender(effect.this.CastTo(Ally), effect)

    return [
        AbilityFactory.WhenUnitWouldAttackUnit(
            AbilityType.NonKeyword,
            "This",
            Enemy,
            swordsman_attack,
            is_basic_attack=True,
        ),
        AbilityFactory.WhenBoostCardTurnedFaceUp(
            AbilityType.HeroResponse,
            None,
            swordsman_defend,
            while_attack=True,
            conditions=[
                lambda effect, message: message.would_atk_message.defender is None,
            ],
        ),
    ]
