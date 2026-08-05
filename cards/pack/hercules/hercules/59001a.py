from . import *


def GetAbilities() -> Sequence['Ability']:

    def atonement(effect: 'Effect', message: 'Message.AfterCardsMoved') -> None:
        player = effect.GetInitiator()
        deck = GetGiftDeck(player)
        if deck:
            gift = deck.GetTop()
            if gift:
                gift.PutIntoPlay(player, effect, under_control=True)
        player.GetIdentity().Ready(effect)
        YouMayFlipToYourAlterEgoForm(player, effect)

    return [
        AbilityFactory.AfterCardsMoved(
            AbilityType.Response,
            CardFinder(trait="LABOR"),
            atonement,
            conditions=[
                lambda effect, message:
                    Worlds.VictoryDisplay(effect) in message.into_areas and
                    any(face.GetOwner() == effect.GetInitiator()
                        for face in message.faces if face.HasTrait("LABOR")),
            ],
        ).SetName("Atonement").LimitOncePerPhase(),
    ]
