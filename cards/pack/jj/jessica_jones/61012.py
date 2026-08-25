from . import *


def GetAbilities() -> Sequence['Ability']:

    def now_im_ticked_off(effect: 'Effect', message: 'Message.AfterEnemyActivationEnd') -> None:
        this = effect.this.CastTo(Upgrade)
        controller = this.GetControlByPlayer()
        controller.GetIdentity().ChangeToForm(Hero, effect)

        targets: List[CardFace] = []
        villain = Worlds.FindVillain(effect)
        if villain:
            targets.append(villain)
        targets += Worlds.GetOnFieldMinions(
            effect,
            CardFinder(engaged_with=message.GetAgainstPlayer()),
        )
        this.DealDamage(targets, 5, effect, property=AttackProperty())
        Faces.DiscardAll([this], effect)

    return [
        AbilityFactory.AfterEnemyActivationEnd(
            AbilityType.ForcedResponse,
            Villain,
            now_im_ticked_off,
            conditions=[
                lambda effect, message: effect.this.GetControlByPlayer().IsAlterEgo(),
            ],
        ).SetLabel("attack"),
    ]
