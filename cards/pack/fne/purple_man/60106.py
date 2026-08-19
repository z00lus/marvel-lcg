from . import *


def GetAbilities() -> Sequence['Ability']:
    def protect(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        villain = Worlds.FindVillain(effect)
        if villain:
            Faces.GiveStatus([villain], "Tough", effect)

    return [
        CommandObligationAbility(
            'Exhaust "Protect." and remove 1 command counter → give the villain Tough',
            protect,
        ),
        PurpleManBoostAbility(),
    ]
