from . import *


def GetAbilities() -> Sequence['Ability']:

    def attack(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        this = effect.this.CastTo(Attachment)
        message.GiveAdditionalBoostCardForThisActivation(1, effect)
        defeated = [False]

        def remove_defeated(face: 'Unit2') -> None:
            defeated[0] = True
            Faces.RemoveAllFromGame([face, this], effect)

        message.IfThisAttackDefeats(Unit2, remove_defeated, effect)

        def finish() -> None:
            if not defeated[0] and this.IsInPlay():
                Faces.ShuffleAllTo([this], "EncounterDeck", effect)

        RunAt.AfterEnemyActivationEnd(effect, message, finish)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(BULLSEYE),
        AbilityFactory.WhenUnitAttackYou(
            AbilityType.ForcedInterrupt,
            BULLSEYE,
            attack,
        ),
    ]
