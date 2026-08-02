from . import *


# Bodyguard

def GetAbilities() -> Sequence['Ability']:
    def bodyguard(effect: 'Effect', message: 'Message.WhenPlayerPayingResources') -> None:
        effect.GetInitiator().DrawUp(1, effect)
        Faces.RemoveAllFromGame([effect.this], effect)

    return [
        AbilityFactory.CanGenerateResources(
            AbilityType.HeroResource,
            Resources("GG"),
            for_card=CardFinder(
                card_type=Event,
                check_face_fn=lambda face: face.HasTrait("DEFENSE") or face.HasTrait("THWART"),
            ),
            ex_operation=bodyguard,
        ),
    ]
