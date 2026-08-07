from . import *

# Know Your Enemy


def GetAbilities() -> Sequence['Ability']:

    def know_your_enemy(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        player = effect.GetInitiator()
        for _ in range(2):
            legal_schemes = [
                scheme for scheme in Worlds.GetOnFieldSchemes(effect)
                if scheme.CanBeThwartBy(effect)
            ]
            scheme = player.AskChooseFace(
                legal_schemes,
                effect,
                prompt="Choose a scheme to remove 1 threat from",
            )
            if scheme:
                this.RemoveThreatFromSchemes([scheme], 1, effect)

    return [
        AbilityFactory.ReduceCostToPlayThis(
            1,
            your_identity_has_traits=["MARTIAL ARTIST"],
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            know_your_enemy,
        ).SetPlay().SetLabel("thwart"),
    ]
