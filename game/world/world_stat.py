from core import *

from game.card.card import *
from game.ability import *
from game.player import *
from game.message import *

class WorldStat:
    def __init__(self) -> None:
        self.once_per_game_effects: List['Effect'] = []
        self.once_per_round_effects: List['Effect'] = []
        self.once_per_round_player_effects: Dict['Player', List['Effect']] = {}
        self.once_per_phase_player_effects: Dict['Player', List['Effect']] = {}
        self.once_per_phase_effects: List['Effect'] = []
        self.this_turn_made_attack: List[Tuple[CardFace, 'Effect', Sequence['CardFace']]] = []
        self.this_turn_made_thwart: List[Tuple[CardFace, 'Effect', Sequence['CardFace']]] = []
        # self.played_cards_this_turn: List[Tuple['Player', 'CardFace']] = []

    def OnTurnBegin(self):
        self.this_turn_made_attack = []
        self.this_turn_made_thwart = []
        # self.played_cards_this_turn = []

    def OnTurnEnd(self):
        self.this_turn_made_attack = []
        self.this_turn_made_thwart = []
        # self.played_cards_this_turn = []

    def OnRoundEnd(self):
        self.once_per_round_effects = []
        self.once_per_round_player_effects = {}

    def OnPhaseEnd(self):
        self.once_per_phase_effects = []
        self.once_per_phase_player_effects = {}

    ################################################################################
    #
    def RecordEffectWithPlayer(self, effect: 'Effect', player: 'Player'):
        if player not in self.once_per_round_player_effects:
            self.once_per_round_player_effects[player] = [effect]
        else:
            self.once_per_round_player_effects[player].append(effect)

        if player not in self.once_per_phase_player_effects:
            self.once_per_phase_player_effects[player] = [effect]
        else:
            self.once_per_phase_player_effects[player].append(effect)

    def RecordEffect(self, effect: 'Effect'):
        self.once_per_game_effects.append(effect)
        self.once_per_round_effects.append(effect)
        self.once_per_phase_effects.append(effect)

    def RecordAttack(self, end_message: 'Message.AfterUnitAttackEnd'):
        self.this_turn_made_attack.append((end_message.attacker, end_message.by_effect, end_message.attacked_targets))

    def RecordThwart(self, end_message: 'Message.AfterUnitThwartEnd'):
        self.this_turn_made_thwart.append((end_message.trigger, end_message.by_effect, end_message.schemes))

    def RecordPlayedCard(self, player: 'Player', face: 'CardFace'):
        # self.played_cards_this_turn.append((player, face))
        pass

    ################################################################################
    # return True means can process
    def IsOncePerGame(self, ability: 'Ability|None') -> bool:
        return ability not in [x.ability for x in self.once_per_game_effects]

    def IsOncePerRound(self, ability: 'Ability|None') -> bool:
        return ability not in [x.ability for x in self.once_per_round_effects]

    def IsOncePerRoundPerPlayer(self, ability: 'Ability|None', player: 'Player') -> bool:
        if player not in self.once_per_round_player_effects:
            return True
        return ability not in [x.ability for x in self.once_per_round_player_effects[player]]

    def IsOncePerPhasePerPlayer(self, ability: 'Ability|None', player: 'Player') -> bool:
        if player not in self.once_per_phase_player_effects:
            return True
        return ability not in [x.ability for x in self.once_per_phase_player_effects[player]]

    def IsOncePerPhase(self, ability: 'Ability|None') -> bool:
        return ability not in [x.ability for x in self.once_per_phase_effects]
