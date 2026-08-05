from . import *


def GetAbilities() -> Sequence['Ability']:

    def draw_cards(effect: 'Effect', message: 'Message.AfterCardEnterPlay') -> None:
        effect.GetInitiator().DrawUp(4, effect)

    return [
        *AbilityFactory.GiveKeywordToAttached("You", health=1),
        AbilityFactory.UnitAttackGainKeyword(
            CardFinder(name="Hercules"),
            is_basic_attack=True,
            piercing=True,
        ),
        AbilityFactory.AfterCardEnterPlay(
            AbilityType.Response,
            "This",
            draw_cards,
        ),
    ]
