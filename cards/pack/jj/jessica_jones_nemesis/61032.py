from . import *


SUGGESTION = CardFinder(card_type=Obligation, set_name="Jessica Jones Nemesis")


def GetAbilities() -> Sequence['Ability']:

    def place_pheromones(faces: Sequence['CardFace'], effect: 'Effect') -> None:
        suggestions = [face for face in faces if face.name.startswith("Suggestion")]
        Faces.PlaceCountersOn(suggestions, 2, PHEROMONE_COUNTER, effect)

    def when_revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        place_pheromones(Worlds.GetOnFieldCards(effect), effect)

    def suggestion_entered(effect: 'Effect', message: 'Message.AfterCardEnterPlay') -> None:
        place_pheromones([message.trigger], effect)

    return [
        AbilityFactory.WhenThisRevealed(None, when_revealed),
        AbilityFactory.AfterCardEnterPlay(
            AbilityType.ForcedResponse,
            SUGGESTION,
            suggestion_entered,
            conditions=[lambda effect, message: message.trigger.name.startswith("Suggestion")],
        ),
    ]
