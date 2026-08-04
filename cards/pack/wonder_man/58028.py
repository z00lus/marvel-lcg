from . import *

# Scythe Strike


def GetAbilities() -> Sequence['Ability']:

    def scythe_strike(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        grim_reaper = Worlds.FindCardOnField(
            effect,
            name="Grim Reaper",
            card_type=Minion,
        )
        if grim_reaper:
            grim_reaper.CastTo(Minion).DoActivate(player, effect)
        else:
            player.GetIdentity().TakeIndirectDamage(this, 2, effect)

    return [
        AbilityFactory.WhenThisRevealed(None, scythe_strike),
    ]
