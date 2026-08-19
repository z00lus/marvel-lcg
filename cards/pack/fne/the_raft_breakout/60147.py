from . import *


def GetAbilities() -> Sequence['Ability']:

    def mysterio(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> None:
        player = message.GetAgainstPlayer()
        if not player:
            return
        for face in list(message.boost_cards):
            if Treachery.IsType(face):
                player.DealEncounterCard(face, effect)

    return [
        AbilityFactory.AfterUnitAttackYou(
            AbilityType.ForcedResponse,
            "This",
            mysterio,
        ),
    ]
