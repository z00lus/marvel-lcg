from . import *

# Creative Solution

def GetAbilities() -> Sequence['Ability']:

    def creative_solution(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        initiator = effect.GetInitiator()
        initiator.DrawUp(1, effect)

        def action(targets: Sequence['CardFace']):
            Faces.DiscardAll(targets, effect)
            for target in targets:
                if not StatusCard.IsType(target):
                    continue
                if target.IsStatusName("Tough"):
                    initiator.ChooseAbilities(
                        effect,
                        AbilityFactory.ForChoiceAbility(
                            "",
                            lambda targets:
                                this.DealDamage(targets, 3, effect)
                        ).SetTarget(Enemy)
                    )
                if target.IsStatusName("Stunned"):
                    initiator.ChooseAbilities(
                        effect,
                        AbilityFactory.ForChoiceAbility(
                            "",
                            lambda targets:
                                this.RemoveThreatFromSchemes(targets, 3, effect)
                        ).SetTarget(Scheme2)
                    )
                if target.IsStatusName("Confused"):
                    initiator.ChooseAbilities(
                        effect,
                        AbilityFactory.ForChoiceAbility(
                            "",
                            lambda targets:
                                this.HealthUnits(targets, 3, effect)
                        ).SetTarget(Identity, canbe_heal=True)
                    )

        action(effect.targets2)


    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            creative_solution
        ).SetPlay().SetLabel()
        .SetTarget2(StatusCard),
    ]
