from . import *


def GetAbilities() -> Sequence['Ability']:

    def alias_investigations(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        this = effect.this.CastTo(Support)
        Faces.PlaceCountersOn([this], 2, EVIDENCE_COUNTER, effect)

        villain = Worlds.FindVillain(effect)
        player = effect.GetInitiator()
        if not villain or this.GetCounters(EVIDENCE_COUNTER) < villain.health:
            return

        player.MayChooseOneAbility(
            effect,
            AbilityFactory.ForChoiceAbility(
                f"Remove {villain.health} evidence counters to defeat {villain}'s current stage",
                lambda targets: Faces.DefeatUnits([villain], player.GetIdentity(), effect),
            ).SetCostFunc(CostFunc.Counter("This", villain.health, EVIDENCE_COUNTER)),
        )

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.Response,
            SchemeSide2,
            alias_investigations,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
