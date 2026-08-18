from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Attachment)
        Players.ForEachPlayer(
            effect,
            lambda player:
                player.GetIdentity().TakeIndirectDamage(this, 1, effect),
        )
        villain = Worlds.FindVillain(effect)
        if villain:
            villain.TakeDamage(
                this,
                2 * Worlds.GetPlayerNumIcon(effect),
                effect,
            )

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(Villain),
        AbilityFactory.WhenThisRevealed(None, revealed),
    ]
