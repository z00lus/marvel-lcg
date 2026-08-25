from . import *


def GetAbilities() -> Sequence['Ability']:

    def big_mistake(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        player = effect.GetInitiator()
        target = list(effect.targets)
        alias = FindAliasInvestigations(effect)
        can_spend = bool(alias and alias.GetCounters(EVIDENCE_COUNTER) >= 1)

        def attack(damage: int, *, overkill: bool=False, piercing: bool=False) -> None:
            this.DealDamage(
                target,
                damage,
                effect,
                property=AttackProperty(overkill=overkill, piercing=piercing),
            )

        def spend_and_attack(*, overkill: bool=False, piercing: bool=False) -> None:
            assert alias
            Faces.RemoveCountersOn([alias], 1, EVIDENCE_COUNTER, effect)
            attack(5, overkill=overkill, piercing=piercing)

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Deal 3 damage",
                lambda targets: attack(3),
            ),
            AbilityFactory.ForChoiceAbility(
                "Remove 1 evidence: deal 5 damage with overkill",
                lambda targets: spend_and_attack(overkill=True),
                condition=can_spend,
            ),
            AbilityFactory.ForChoiceAbility(
                "Remove 1 evidence: deal 5 damage with piercing",
                lambda targets: spend_and_attack(piercing=True),
                condition=can_spend,
            ),
        )

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            big_mistake,
        ).SetPlay().SetLabel("attack").SetTarget(Enemy),
    ]
