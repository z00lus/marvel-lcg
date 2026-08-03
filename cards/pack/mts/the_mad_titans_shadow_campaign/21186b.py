from . import *


def GetAbilities() -> Sequence['Ability']:
    def first_player_does_not_control_odin(
        effect: 'Effect',
        message: 'Message.WhenSchemeWouldRemoveThreat',
    ) -> bool:
        odin = Worlds.FindCardOnField(effect, name="Odin", card_type=Ally)
        return not odin or odin.GetControlByPlayer() != Worlds.GetFirstPlayer(effect)

    def retrieve_odins_armor(
        effect: 'Effect',
        message: 'Message.WhenSchemeBeDefeated',
    ) -> None:
        odin = Worlds.FindCardOnField(effect, name="Odin", card_type=Ally)
        if odin:
            effect.this.HealthUnits([odin], "All", effect)
            if odin.HasTrait("WOUNDED"):
                odin.card.Flip(effect)

    return [
        AbilityFactory.ThreatCannotBeRemovedFromWhile(
            "This",
            conditions=[first_player_does_not_control_odin],
        ),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            retrieve_odins_armor,
        ),
    ]
