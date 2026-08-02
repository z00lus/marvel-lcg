from . import *


# War Cry

def GetAbilities() -> Sequence['Ability']:
    def war_cry(effect: 'Effect', message: 'Message.WhenPlayerPayingResources') -> None:
        Faces.GiveStatus([effect.GetInitiator().GetIdentity()], "Tough", effect)
        Faces.RemoveAllFromGame([effect.this], effect)

    return [
        AbilityFactory.CanGenerateResources(
            AbilityType.HeroResource,
            Resources("GG"),
            for_card=CardFinder(
                card_type=Event,
                check_face_fn=lambda face: face.HasTrait("ATTACK") or face.HasTrait("DEFENSE"),
            ),
            ex_operation=war_cry,
        ),
    ]
