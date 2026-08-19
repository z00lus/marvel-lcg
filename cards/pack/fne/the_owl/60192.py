from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Minion)
        identity = Filter.One(
            [player.GetIdentity() for player in Worlds.GetPlayers(effect)],
            effect,
            fewest_remaining_hp=True,
        )
        if identity:
            this.EngagePlayer(identity.GetControlByPlayer(), effect)

    return [
        PiercingAttackAbility(ranged=True),
        AbilityFactory.WhenThisRevealed(None, revealed),
    ]
