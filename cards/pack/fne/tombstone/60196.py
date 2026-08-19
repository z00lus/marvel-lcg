from . import *


def GetAbilities() -> Sequence['Ability']:

    def hard_as_marble(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> None:
        Faces.GiveStatus(message.attacked_targets, "Stunned", effect)
        Faces.DiscardAll([effect.this], effect)

    return [
        AttachToHighestHpMinionAndGiveTough(),
        AbilityFactory.AfterUnitAttackEnd(
            AbilityType.ForcedResponse,
            "AttachedMinion",
            hard_as_marble,
        ),
    ]
