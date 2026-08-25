from . import *


def GetAbilities() -> Sequence['Ability']:

    def can_discard(effect: 'Effect', face: 'CardFace') -> bool:
        return Minion.IsType(face) and max(0, face.health - 2) <= EvidenceCount(effect)

    def digital_camcorder(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        minion = effect.targets[0].CastTo(Minion)
        evidence = max(0, minion.health - 2)
        alias = FindAliasInvestigations(effect)
        assert alias
        if evidence:
            Faces.RemoveCountersOn([alias], evidence, EVIDENCE_COUNTER, effect)
        Faces.DiscardAll([minion], effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.AlterEgoAction,
            digital_camcorder,
        ).SetTarget(
            Minion,
            non_trait="ELITE",
            canbe_discard=True,
            check_fn=can_discard,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
