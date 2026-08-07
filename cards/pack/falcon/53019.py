from . import *

# Strength in Diversity

def GetAbilities() -> Sequence['Ability']:

    def strength_in_diversity(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        initiator = effect.GetInitiator()

        faces = Worlds.GetOnFieldFriendlyCharacters(effect)
        value = Faces.CountTraitNum(faces)

        initiator.ChooseForEach(
            effect,
            value,
            lambda _index: [
                AbilityFactory.ForChoiceAbility(
                    "Remove 1 threat from a scheme",
                    lambda targets:
                        this.RemoveThreatFromSchemes(targets, 1, effect)
                ).SetTarget(Scheme2),
                AbilityFactory.ForChoiceAbility(
                    "Deal 1 damage to an enemy",
                    lambda targets:
                        this.DealDamage(targets, 1, effect)
                ).SetTarget(Enemy),
            ],
        )


    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            strength_in_diversity
        ).SetPlay().SetLabel(),
    ]
