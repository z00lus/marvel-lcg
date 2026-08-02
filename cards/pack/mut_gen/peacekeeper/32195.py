from . import *


# Fortitude

def GetAbilities() -> Sequence['Ability']:
    def fortitude(effect: 'Effect', message: 'Message.WhenPlayerPayingResources') -> None:
        player = effect.GetInitiator()
        enemy = player.AskChooseFace(Worlds.GetOnFieldEnemies(effect), effect, prompt="Choose an enemy to stun")
        if enemy:
            Faces.GiveStatus([enemy], "Stunned", effect)
        Faces.RemoveAllFromGame([effect.this], effect)

    return [
        AbilityFactory.CanGenerateResources(
            AbilityType.HeroResource,
            Resources("GG"),
            for_card=CardFinder(
                card_type=Event,
                check_face_fn=lambda face: face.HasTrait("TACTIC") or face.HasTrait("THWART"),
            ),
            ex_operation=fortitude,
        ),
    ]
