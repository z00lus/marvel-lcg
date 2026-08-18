from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(SchemeSide2)
        bullseye = Worlds.FindCardOnField(effect, BULLSEYE)
        if bullseye:
            this.PlaceThreatOnSchemes([this], bullseye.printed_stage, effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        this = effect.this
        player = message.GetToPlayer()
        message.AfterThisActivation(effect, lambda: this.Reveal(player, effect))

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
