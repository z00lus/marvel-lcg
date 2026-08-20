from . import *


def GetAbilities() -> Sequence['Ability']:
    def attach(effect: 'Effect', villain: 'CardFace') -> None:
        player = Worlds.GetCurrentPlayer(effect)
        Faces.GiveStatus([player.GetIdentity()], "Confused", effect)

    def discard_and_attack(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this
        player = message.GetToPlayer()
        Faces.DiscardAll([this], effect)
        villain = Worlds.FindVillain(effect)
        if villain:
            villain.DoAttackYou(player, effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        identity = message.GetToPlayer().GetIdentity()
        if not Faces.GiveStatus([identity], "Confused", effect):
            scheme = Worlds.FindMainScheme(effect)
            if scheme:
                scheme.PlaceThreat(1, effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(KINGPIN, when_attach_operation=attach),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            discard_and_attack,
        ).SetCostFunc(CostFunc.Discard("YourHandCards", trait="ATTACK", card_type=Event)),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
