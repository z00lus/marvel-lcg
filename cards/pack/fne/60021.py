from . import *

# * Dagger


def GetAbilities() -> Sequence['Ability']:

    def dagger(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        message.PreventDamage(1, effect)

    return [
        *AbilityFactory.GiveKeywordToInPlayWhenApplyThis(
            CardFinder(name="Cloak"),
            acceleration_icon=-1,
        ),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.ForcedInterrupt,
            "This",
            dagger,
            is_consequential_damage=True,
            conditions=[
                lambda effect, message:
                    Worlds.FindCardOnField(effect, name="Cloak") is not None
            ],
        ),
    ]
