from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        Players.ForEachPlayer(effect, lambda player: RevealNemesisOrUnderling(effect, player))
        if Worlds.IsExpert(effect):
            scheme = Search.EncounterCard(
                effect,
                "FirstPlayer",
                include_discard_pile=True,
                include_set_aside=True,
                name="Organized Crime",
                card_type=EncounterSideScheme,
            )
            if scheme:
                scheme.Reveal("FirstPlayer", effect)

    return [AbilityFactory.WhenThisRevealed(None, revealed)]
