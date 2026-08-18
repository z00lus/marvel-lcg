from . import *


def GetAbilities() -> Sequence['Ability']:

    def change_attack_keywords(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        message.property.ranged = False
        message.GainPiercing(effect)

    def discard(effect: 'Effect', message: 'Message.AfterUnitDefendEnd') -> None:
        Faces.DiscardAll([effect.this], effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(BULLSEYE),
        AbilityFactory.WhenUnitAttackYou(
            AbilityType.ForcedInterrupt,
            BULLSEYE,
            change_attack_keywords,
        ),
        AbilityFactory.AfterUnitDefendAgainstAttack(
            AbilityType.HeroResponse,
            "YourHero",
            discard,
            attacker=BULLSEYE,
        ).SetCost(Cost("2", different_type=True)),
    ]
