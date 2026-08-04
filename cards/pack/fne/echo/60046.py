from . import *

# Improvisation


def GetAbilities() -> Sequence['Ability']:

    def improvisation(effect: 'Effect', message: 'Message.AfterPlayerPlayedCard') -> None:
        this = effect.this.CastTo(Upgrade)
        event = message.played_face
        initiator = effect.GetInitiator()
        identity = initiator.GetIdentity()

        if event.HasTrait("ATTACK"):
            this.HealthUnits([identity], 1, effect)

        if event.HasTrait("DEFENSE"):
            schemes = Worlds.GetOnFieldSchemes(effect)
            scheme = initiator.AskChooseFace(schemes, effect)
            if scheme:
                this.RemoveThreatFromSchemes([scheme], 1, effect)

        if event.HasTrait("THWART"):
            enemy = initiator.AskChooseFace(Worlds.GetOnFieldEnemies(effect), effect)
            if enemy:
                this.DealDamage([enemy], 1, effect)

    return [
        AbilityFactory.AfterPlayerPlayedCard(
            AbilityType.HeroResponse,
            "You",
            Event,
            improvisation,
            conditions=[
                lambda effect, message:
                    any(message.played_face.HasTrait(trait) for trait in ["ATTACK", "DEFENSE", "THWART"])
            ],
        ),
    ]
