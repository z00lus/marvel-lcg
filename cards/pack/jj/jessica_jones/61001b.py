from . import *


def GetAbilities() -> Sequence['Ability']:

    def incognito_mode(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        identity = player.GetIdentity()
        identity.ChangeToForm(Hero, effect)
        identity.effect.RegisterTemp(
            AbilityFactory.PlayersCannotChangeForms(
                AbilityType.Temp0,
                "You",
                from_form=Hero,
                to_form=AlterEgo,
            ),
            unregister_after_exec=False,
            until_phase_end=True,
        )

    return [
        AbilityFactory.SetupPutIntoPlay(["61002"]),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.AlterEgoAction,
            incognito_mode,
        ).LimitOncePerPhase(),
    ]
