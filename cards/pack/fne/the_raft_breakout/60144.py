from . import *


def GetAbilities() -> Sequence['Ability']:

    def absorbing_man(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        this = effect.this.CastTo(Minion)
        player = message.GetAgainstPlayer()
        if not player:
            return
        top_card = player.player_deck.GetTop()
        if top_card:
            this.TuckCardUnderHere(top_card, effect)
        resource_types = FacesCounter.GetPrintedResourcesTypes(
            this.GetPlacedCardArea().GetAll()
        )
        if resource_types:
            message.GainAttackForThisAttack(resource_types, effect)

    return [
        AbilityFactory.WhenUnitWouldAttack(
            AbilityType.ForcedInterrupt,
            "This",
            absorbing_man,
        ),
    ]
