from . import *


def GetAbilities() -> Sequence['Ability']:
    def attach(effect: 'Effect', villain: 'CardFace') -> None:
        villain.CastTo(Villain).GiveFacedownBoostCardsInternal(1, effect, None)

    def discard_and_scheme(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this
        player = message.GetToPlayer()
        Faces.DiscardAll([this], effect)
        villain = Worlds.FindVillain(effect)
        if villain:
            villain.DoSchemes(player, effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(KINGPIN, when_attach_operation=attach),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            discard_and_scheme,
        ).SetCostFunc(CostFunc.Discard("YourHandCards", trait="THWART", card_type=Event)),
        AbilityFactory.WhenThisBoostAttachTo(KINGPIN),
    ]
