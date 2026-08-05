from . import *

# * Nelson and Murdock


def GetAbilities() -> Sequence['Ability']:

    def nelson_and_murdock(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        Faces.GiveStatus(effect.targets, "Confused", effect)

    return [
        AbilityFactory.CanPlayThisSupportCard(),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.Response,
            EncounterSideScheme,
            nelson_and_murdock,
            conditions=[
                lambda effect, message:
                    message.killer is not None and
                    (Unit2.IsType(message.killer) or Support.IsType(message.killer)) and
                    message.killer.HasTrait("ATTORNEY")
            ],
        ).SetTarget(Enemy, canbe_confused=True),
    ]
