from . import *

# Death Cannot Die


def GetAbilities() -> Sequence['Ability']:

    def death_cannot_die(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        grim_reaper = Worlds.FindCardOnField(
            effect,
            name="Grim Reaper",
            card_type=Minion,
        )
        if grim_reaper:
            grim_reaper.CastTo(Minion).DoActivate(player, effect)
        else:
            Find.FindAndReveal(
                effect,
                player,
                name="Grim Reaper",
                card_type=Minion,
            )

    def death_cannot_die_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        player = message.GetToPlayer()
        grim_reaper = Worlds.FindCardOnField(
            effect,
            name="Grim Reaper",
            card_type=Minion,
        )
        if grim_reaper:
            message.AfterThisActivation(
                effect,
                lambda: grim_reaper.CastTo(Minion).DoActivate(player, effect),
            )

    return [
        AbilityFactory.WhenThisRevealed(None, death_cannot_die),
        AbilityFactory.WhenCardBecomeBoost("This", death_cannot_die_boost),
    ]
