from . import *


def GetAbilities() -> Sequence['Ability']:
    def safehouse_established(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Environment)
        if not Faces.RemoveCountersOn([this], 1, 'safehouse', effect):
            return

        card = CardFactory.GenerateCard("40197", None, effect.world)
        card.face.PutIntoPlay(Worlds.GetFirstPlayer(effect), effect, under_control=True)

    return [
        AbilityFactory.ThisEnterPlayWithCounters(1, 'safehouse'),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            safehouse_established,
        ).AnyPlayerCanDoThis()
        .SetTarget("This", has_counter='safehouse'),
    ]
