from . import *


def GetAbilities() -> Sequence['Ability']:

    def son_of_zeus(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        identity = player.GetIdentity()
        identity.Ready(effect)

        gifts = CountGifts(player)
        if gifts >= 1:
            upgrades = player.GetControlCards(
                CardFinder(card_type=Upgrade, card_class="IdentitySpecific", canbe_ready=True),
            )
            if upgrades:
                player.AskChooseOneText(upgrades).Ready(effect)
        if gifts >= 2:
            Faces.GiveStatus([identity], "Tough", effect)
        if gifts >= 3:
            player.DrawUp(1, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            son_of_zeus,
        ).SetPlay(),
    ]
