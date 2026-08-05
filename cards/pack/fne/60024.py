from . import *

# * De-escalation


def GetAbilities() -> Sequence['Ability']:

    def de_escalation(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        player = effect.GetInitiator()
        schemes = [
            scheme for scheme in Worlds.GetMainSchemes(effect)
            if scheme.acceleration_token > 0
        ]
        scheme = player.AskChooseFace(
            schemes,
            effect,
            prompt="Choose a scheme to remove an acceleration token from",
        ) if schemes else None
        if scheme:
            Faces.RemoveTokensOn([scheme], 1, "acceleration_token", effect)

    return [
        AbilityFactory.CanPlayThisSchemeCard(),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            de_escalation,
        ),
    ]
