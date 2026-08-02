from . import *


# Improvisation

def GetAbilities() -> Sequence['Ability']:
    def improvisation(effect: 'Effect', message: 'Message.WhenPlayerPayingResources') -> None:
        player = effect.GetInitiator()
        allies = player.GetControlAllies(CardFinder(canbe_ready=True)|CardFinder(canbe_heal=True))
        ally = player.AskChooseFace(allies, effect, prompt="Choose an ally to ready and heal")
        if ally:
            Faces.ReadyAll([ally], effect)
            effect.this.HealthUnits([ally], 2, effect)
        Faces.RemoveAllFromGame([effect.this], effect)

    return [
        AbilityFactory.CanGenerateResources(
            AbilityType.HeroResource,
            Resources("GG"),
            for_card=CardFinder(
                card_type=Event,
                check_face_fn=lambda face: face.HasTrait("ATTACK") or face.HasTrait("TACTIC"),
            ),
            ex_operation=improvisation,
        ),
    ]
