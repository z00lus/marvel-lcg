from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.ReduceCostToPlayFaceWhen(
            Event,
            1,
            "AnyPlayer",
            conditions=[
                lambda effect, message:
                    message.check_effect.this.CastTo(Event).printed_cost.val >= 3,
            ],
        ),
    ]
