from . import *

# Enhanced Olfaction


def GetAbilities() -> Sequence['Ability']:

    def enhanced_olfaction(effect: 'Effect') -> None:
        Faces.DiscardAll([effect.this], effect)
        Worlds.UpdateNextCardPlayCost(
            effect.GetInitiator(),
            -2,
            effect,
            in_this="Phase",
        )

    return [
        SenseCanAttachToEnemyOrScheme(),
        *SenseCompletionAbilities(enhanced_olfaction),
    ]
