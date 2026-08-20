from . import *


def GetAbilities() -> Sequence['Ability']:
    def setup(effect: 'Effect', message: 'Message.AfterCardEnterPlay') -> None:
        villain = Worlds.FindVillain(effect)
        if villain and Rand.RandomChoice([False, True], effect):
            villain.card.Flip(effect, call_reveal=False)

    def flip_villain(effect: 'Effect', message: 'Message.WhenPhaseEnd') -> None:
        villain = Worlds.FindVillain(effect)
        if villain:
            villain.card.Flip(effect, call_reveal=False)

    return [
        AbilityFactory.AfterCardEnterPlay(
            AbilityType.ForcedResponse,
            "This",
            setup,
        ),
        AbilityFactory.WhenVillainPhaseEnd(
            AbilityType.ForcedInterrupt,
            flip_villain,
        ),
    ]
