from . import *


def GetAbilities() -> Sequence['Ability']:
    def defeated(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        player = message.GetDefeatingPlayer()
        scheme = Worlds.FindCardOnField(
            effect,
            card_type=EncounterSideScheme,
            is_nemesis=player,
        )
        if scheme:
            scheme.PlaceThreat(3, effect)
            return
        scheme = Search.EncounterCard(
            effect,
            player,
            include_discard_pile=True,
            include_set_aside=True,
            card_type=EncounterSideScheme,
            is_nemesis=player,
        )
        if scheme:
            scheme.Reveal(player, effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            defeated,
            has_defeating_player=True,
        ),
    ]
