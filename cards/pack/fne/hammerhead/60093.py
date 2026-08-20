from . import *


def GetAbilities() -> Sequence['Ability']:
    def underboss(effect: 'Effect', message: 'Message.WhenEnemyActivateAgainstYou') -> None:
        if message.GetToPlayer().GetIdentity().IsStunned():
            message.GiveAdditionalBoostCardForThisActivation(1, effect)

    return [
        AbilityFactory.WhenEnemyActivateAgainstYou(
            AbilityType.ForcedInterrupt,
            "This",
            underboss,
        ),
    ]
