from . import *


def GetAbilities() -> Sequence['Ability']:
    def attack(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        hammerhead = Worlds.FindCardOnField(effect, HAMMERHEAD)
        if not hammerhead:
            return
        stunned = player.GetIdentity().IsStunned()
        hammerhead.CastTo(Villain).DoAttackYou(
            player,
            effect,
            property=AttackProperty(
                additional_value=2 if stunned else 0,
                overkill=stunned,
            ),
        )

    return [
        AbilityFactory.WhenThisRevealed("Alter-Ego", ThisCardGainSurge),
        AbilityFactory.WhenThisRevealed("Hero", attack),
    ]
