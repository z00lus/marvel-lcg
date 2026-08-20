from . import *


def GetAbilities() -> Sequence['Ability']:
    def attach(effect: 'Effect', villain: 'CardFace') -> None:
        player = Worlds.GetCurrentPlayer(effect)
        Faces.GiveStatus([player.GetIdentity()], "Stunned", effect)

    def after_attack(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> None:
        if Faces.GiveStatus([message.attacked], "Stunned", effect):
            Faces.DiscardAll([effect.this], effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        identity = message.GetToPlayer().GetIdentity()
        if not Faces.GiveStatus([identity], "Stunned", effect):
            identity.TakeDamage(effect.this, 1, effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(KINGPIN, when_attach_operation=attach),
        AbilityFactory.AfterUnitAttackUnit(
            AbilityType.ForcedResponse,
            KINGPIN,
            Hero,
            after_attack,
            target_took_damage=True,
        ),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
