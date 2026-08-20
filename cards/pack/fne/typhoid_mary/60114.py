from . import *


def GetAbilities() -> Sequence['Ability']:
    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        if not IsActivatingMary(message, "Typhoid Mary"):
            return
        player = message.GetToPlayer()

        def exhaust_damaged(damage_message: 'Message.AfterUnitTookDamage') -> None:
            Faces.ExhaustAll([damage_message.trigger], effect)

        player.GetIdentity().TakeIndirectDamage(
            effect.this,
            3,
            effect,
            operation=exhaust_damaged,
        )

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(Villain),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.HeroAction,
        ).SetCost(Cost("BB")),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
