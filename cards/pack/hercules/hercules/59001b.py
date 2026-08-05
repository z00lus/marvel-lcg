from . import *


def GetAbilities() -> Sequence['Ability']:

    def reveal_labor(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        deck = GetLaborDeck(player)
        if deck:
            face = deck.GetTop()
            if face:
                face.Reveal(player, effect)

    def no_labor_in_play(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> bool:
        return not effect.world.FindCardsOnField(
            finder=CardFinder(trait="LABOR"),
            owner=effect.GetInitiator(),
        )

    return [
        AbilityFactory.BeginGameWithSetAside(
            ["59002", "59003", "59004", "59005", "59006", "59007"],
            SetupHerculesSpecialDecks,
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            reveal_labor,
            conditions=[no_labor_in_play],
        ).SetName("New Labors of Hercules"),
    ]
