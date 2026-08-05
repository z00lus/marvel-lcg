from . import *

# Chance Encounter


def GetAbilities() -> Sequence['Ability']:

    def chance_encounter(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        player = effect.GetInitiator()
        ally = Search.PlayerCard(
            effect,
            player,
            include_player_deck=True,
            include_discard_pile=True,
            card_type=Ally,
        )
        if ally:
            Faces.AddToHand([ally], player, effect)

    return [
        AbilityFactory.CanPlayThisUpgradeCard(SchemeSide2),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.Interrupt,
            "AttachedScheme",
            chance_encounter,
        ),
    ]
