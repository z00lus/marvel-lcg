from . import *


def GetAbilities() -> Sequence['Ability']:

    def breakthrough(effect: 'Effect', message: 'Message.AfterCardPlacedCounter') -> None:
        this = effect.this.CastTo(Event)
        player = effect.GetInitiator()
        Faces.ReadyAll([player.GetIdentity()], effect)
        Faces.ShuffleAllTo([this], player.player_deck, effect)

    return [
        AbilityFactory.AfterCounterPlacedOn(
            AbilityType.Response,
            CardFinder(name="Alias Investigations"),
            EVIDENCE_COUNTER,
            breakthrough,
        ).SetPlay(),
    ]
