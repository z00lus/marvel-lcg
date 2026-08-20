from . import *


def GetAbilities() -> Sequence['Ability']:
    def attack_again(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> None:
        this = effect.this.CastTo(Attachment)
        target = message.attacked
        hammerhead = Worlds.FindCardOnField(effect, HAMMERHEAD)
        if not hammerhead or not target.IsInPlay():
            return
        Faces.DiscardAll([this], effect)
        hammerhead.CastTo(Villain).BasicAttack([target], effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(HAMMERHEAD),
        AbilityFactory.AfterUnitAttackUnit(
            AbilityType.ForcedResponse,
            HAMMERHEAD,
            Friend,
            attack_again,
            conditions=[lambda effect, message: message.attacked.IsInPlay()],
        ),
    ]
