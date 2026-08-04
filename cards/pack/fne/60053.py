from . import *

# * Ronin


def GetAbilities() -> Sequence['Ability']:

    def no_allies(effect: 'Effect', face: 'CardFace', ui: List['CardFace']) -> int:
        return int(len(effect.GetInitiator().GetControlAllies()) == 0)

    return [
        *AbilityFactory.GiveKeywordToAttached(
            "You",
            get_new_value=no_allies,
            defense=1,
            retaliate=1,
            ex_change_on_event=OnEvent.PlayAreaCard("YouControlCards"),
        ),
    ]
