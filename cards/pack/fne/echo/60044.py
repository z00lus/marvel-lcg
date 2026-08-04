from . import *

# Choreography


def GetAbilities() -> Sequence['Ability']:

    def choreography(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Upgrade)
        Unused(this)

        initiator = effect.GetInitiator()
        Faces.ShuffleAllTo(effect.targets, initiator.player_deck, effect)
        if initiator.IsAlterEgo():
            initiator.DrawUp(1, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            choreography,
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetTarget(
            CardFinder(check_face_fn=IsAspectOrBasicEvent),
            from_where=["YourDiscardPile"],
        ),
    ]
