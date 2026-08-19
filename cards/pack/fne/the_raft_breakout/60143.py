from . import *


def GetAbilities() -> Sequence['Ability']:

    def master_key(effect: 'Effect', message: 'Message.AfterUnitSchemeEnd') -> None:
        player = message.GetAgainstPlayer()
        if not player:
            return
        for face in list(message.boost_cards):
            if Minion.IsType(face):
                player.DealEncounterCard(face, effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(Villain),
        AbilityFactory.AfterUnitSchemeAgainst(
            AbilityType.ForcedResponse,
            Villain,
            "AnyPlayer",
            master_key,
        ),
    ]
