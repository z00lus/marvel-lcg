from . import *


def GetAbilities() -> Sequence['Ability']:

    def wanted(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Obligation)
        player = effect.GetInitiator()
        minion = Worlds.DiscardEncounterCardsUntil(
            effect,
            card_type=Minion,
            trait="POLICE",
        )
        if minion:
            minion.PutIntoPlay(player, effect)
        Faces.DiscardAll([this], effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            wanted,
        ),
    ]
