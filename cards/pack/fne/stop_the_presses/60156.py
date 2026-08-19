from . import *


def GetAbilities() -> Sequence['Ability']:

    def robbie_robertson(
        effect: 'Effect',
        message: 'Message.AfterPlayerDealEncounterCard',
    ) -> None:
        player = message.GetToPlayer()
        encounter_card = message.would_message.face
        Faces.LookAt([encounter_card], effect.GetInitiator(), effect)
        if effect.GetInitiator().MayChooseFace(
            [encounter_card],
            effect,
            not_move=True,
        ):
            Faces.DiscardAll([encounter_card], effect)
            player.DealEncounterCards(1, effect)

    return [
        AbilityFactory.AfterPlayerDealEncounterCard(
            AbilityType.Response,
            robbie_robertson,
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetCostFunc(CostFunc.Counter("This", 1, STAMINA)),
    ]
