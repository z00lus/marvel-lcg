from . import *


def GetAbilities() -> Sequence['Ability']:
    def attack(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        message.GainPiercing(effect)

    def defeated(effect: 'Effect', message: 'Message.WhenUnitBeDefeated') -> None:
        assets = [
            face for face in Worlds.GetOnFieldCards(effect)
            if isinstance(face, Support|Upgrade)
        ]
        asset = Filter.One(assets, effect, highest_cost=True)
        if asset:
            Faces.DiscardAll([asset], effect)

    return [
        AbilityFactory.WhenUnitWouldAttack(
            AbilityType.ForcedInterrupt,
            "This",
            attack,
        ),
        AbilityFactory.WhenUnitBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            defeated,
        ),
        PurpleManBoostAbility(),
    ]
