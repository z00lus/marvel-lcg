from game.card.face import *
from game.ability import *
from game.message import *
from game.player import *

def GetForDelayAbility(effect: 'Effect') -> 'Ability|None':
    # if effect.ability.type.is_delay_ability:
    #     return effect.delay_ability
    return effect.ability

class ConditionOncePer:

    @staticmethod
    def LimitOncePerGame(effect: 'Effect', message: 'Message2') -> bool:
        world = effect.world
        ability = GetForDelayAbility(effect)
        return world.stat.IsOncePerGame(ability)

    @staticmethod
    def LimitOncePerRound(effect: 'Effect', message: 'Message2') -> bool:
        world = effect.world
        ability = GetForDelayAbility(effect)
        return world.stat.IsOncePerRound(ability)

    @staticmethod
    def LimitOncePerRoundPerPlayer(effect: 'Effect', message: 'Message2') -> bool:
        from game.message.sender.sender import TriggerNonePlayerMessage
        assert isinstance(message, TriggerNonePlayerMessage)
        world = effect.world
        player = message.GetToPlayer()
        ability = GetForDelayAbility(effect)
        return world.stat.IsOncePerRoundPerPlayer(ability, player)

    @staticmethod
    def LimitOncePerPhasePerPlayer(effect: 'Effect', message: 'Message2') -> bool:
        from game.message.sender.sender import TriggerNonePlayerMessage
        assert isinstance(message, TriggerNonePlayerMessage)
        world = effect.world
        player = message.GetToPlayer()
        ability = GetForDelayAbility(effect)
        return world.stat.IsOncePerPhasePerPlayer(ability, player)

    @staticmethod
    def LimitOncePerPhase(effect: 'Effect', message: 'Message2') -> bool:
        world = effect.world
        ability = GetForDelayAbility(effect)
        return world.stat.IsOncePerPhase(ability)

    @staticmethod
    def LimitOncePerEvent(effect: 'Effect', message: 'Message2') -> bool:
        ability = GetForDelayAbility(effect)
        return ability not in [x.ability for x in message.once_per_event_effects]

    @staticmethod
    def LimitOnceCardNamePerEvent(effect: 'Effect', message: 'Message2') -> bool:
        ability = GetForDelayAbility(effect)
        if ability == None:
            return True
        return ability.paper not in [x.ability.paper for x in message.once_per_event_effects]
