from . import *


def GetAbilities() -> Sequence['Ability']:
    def black_swan(
        effect: 'Effect',
        message: 'Message.AfterMinionEngagePlayer',
    ) -> None:
        message.engaged_player.DiscardRandomHandCards(1, effect)

    return [
        AbilityFactory.ThisMinionEngageFirstPlayer(),
        AbilityFactory.AfterMinionEngagePlayer(
            AbilityType.ForcedResponse,
            "This",
            None,
            black_swan,
        ),
    ]
