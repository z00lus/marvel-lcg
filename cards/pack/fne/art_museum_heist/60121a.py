from . import *


def GetAbilities() -> Sequence['Ability']:

    def setup(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        villain = Worlds.FindVillain(effect)
        encounter_deck = Worlds.GetEncounterDeck(effect)
        arts = encounter_deck.FindCards(ART)
        art = Rand.RandomChoice(arts, effect) if arts else None
        if villain and art:
            art.AttachTo2(villain, effect)
            encounter_deck.Shuffle(effect)

    return [AbilityFactory.WhenCardSetup("This", setup)]
