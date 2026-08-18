from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        Find.FindAndReveal(
            effect,
            message.GetToPlayer(),
            trait="POLICE",
            card_type=Minion,
        )

    return [
        *AbilityFactory.GiveKeywordToInPlayWhenApplyThis(
            POLICE,
            guard=1,
            patrol=1,
        ),
        AbilityFactory.WhenThisRevealed(None, revealed),
    ]
