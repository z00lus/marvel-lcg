from . import *

# Acute Tactility


def GetAbilities() -> Sequence['Ability']:

    def acute_tactility(effect: 'Effect') -> None:
        Faces.DiscardAll([effect.this], effect)
        Faces.ReadyAll([effect.GetInitiator().GetIdentity()], effect)

    return [
        SenseCanAttachToEnemyOrScheme(),
        *SenseCompletionAbilities(acute_tactility),
    ]
