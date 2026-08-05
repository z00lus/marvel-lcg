from . import *

# Deposition


def GetAbilities() -> Sequence['Ability']:

    def deposition(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        player = effect.GetInitiator()
        ChooseAndPlaySense(player, effect, optional=True)
        this.RemoveThreatFromSchemes(effect.targets, 2, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.AlterEgoAction,
            deposition,
        ).SetPlay().SetLabel("thwart").SetTarget(Scheme2),
    ]
