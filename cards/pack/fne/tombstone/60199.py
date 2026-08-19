from . import *


def GetAbilities() -> Sequence['Ability']:

    def hit_list(effect: 'Effect', message: 'Message.AfterPhaseBegin') -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        first_player = Worlds.GetFirstPlayer(effect)
        damage_messages = first_player.GetIdentity().TakeIndirectDamage(
            this,
            3,
            effect,
        )
        defeated_allies = sum(
            1 for damage_message in damage_messages
            if isinstance(damage_message, Message.AfterUnitDefeatedUnit)
            and Ally.IsType(damage_message.target)
        )
        if defeated_allies:
            this.RemoveThreatFromSchemes(
                [this],
                defeated_allies,
                effect,
                ignore_crisis=True,
            )

    return [
        AbilityFactory.AfterPhaseBegin(
            AbilityType.ForcedResponse,
            "Villain",
            hit_list,
        ),
    ]
