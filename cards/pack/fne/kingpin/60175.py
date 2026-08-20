from . import *


def GetAbilities() -> Sequence['Ability']:
    def random_nemesis(effect: 'Effect', player: 'Player') -> 'CardFace|None':
        faces = player.set_aside_nemesis_sets.Get(True)
        return Rand.RandomChoice(faces, effect) if faces else None

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        face = random_nemesis(effect, message.GetToPlayer())
        if face:
            face.Reveal(message.GetToPlayer(), effect)
        else:
            effect.this.GainSurge(1, effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        face = random_nemesis(effect, message.GetToPlayer())
        if face:
            message.activating_enemy.GiveBoostCard(
                face,
                effect,
                message.being_message.would_message,
            )

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
