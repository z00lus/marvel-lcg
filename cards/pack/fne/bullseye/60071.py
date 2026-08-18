from . import *


def GetAbilities() -> Sequence['Ability']:

    def redirect(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        this = effect.this.CastTo(Attachment)
        ally = this.GetBindFace()
        message.ReplaceTarget(ally)
        message.GainOverKill(effect)
        message.IfThisAttackDefeats(
            ally,
            lambda face: Faces.RemoveAllFromGame([face], effect),
            effect,
        )

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            "YourAlly",
            without_another_copy=True,
            if_cannot_gain_surge=True,
        ),
        AbilityFactory.WhenUnitWouldAttack(
            AbilityType.ForcedInterrupt,
            Villain,
            redirect,
            conditions=[
                lambda effect, message:
                    message.GetToPlayer() == effect.this.CastTo(Attachment).GetBindFace().GetControlByPlayer(),
            ],
        ),
    ]
