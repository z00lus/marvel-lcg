from . import *


def GetAbilities() -> Sequence['Ability']:

    def draw_cards(effect: 'Effect', message: 'Message.AfterCardEnterPlay') -> None:
        effect.GetInitiator().DrawUp(4, effect)

    return [
        *AbilityFactory.GiveKeywordToAttached("You", health=1, retaliate=1),
        AbilityFactory.AfterCardEnterPlay(
            AbilityType.Response,
            "This",
            draw_cards,
        ),
    ]
