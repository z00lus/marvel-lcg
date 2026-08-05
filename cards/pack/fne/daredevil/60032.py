from . import *

# Sensory Overload


def GetAbilities() -> Sequence['Ability']:

    def sensory_overload(effect: 'Effect', message: 'Message.AfterCardEnterPlay') -> None:
        identity = effect.GetInitiator().GetIdentity()
        identity.TakeDamage(effect.this, 1, effect)

    return [
        AbilityFactory.AfterCardEnterPlay(
            AbilityType.ForcedResponse,
            CardFinder(trait="SENSE"),
            sensory_overload,
            conditions=[
                lambda effect, message:
                    message.trigger.GetOwnerPlayer() == effect.GetInitiator()
            ],
        ),
        AbilityFactory.AfterUnitRecovery(
            AbilityType.AlterEgoResponse,
            "You",
            DiscardThisCard,
        ),
    ]
