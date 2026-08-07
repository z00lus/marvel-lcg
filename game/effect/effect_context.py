from core import *
from game.card.face import *
from game.effect import *
from game.message import *
from game.player import *
from game.world import *
from game.element.resources import Resources
from game.element.cost import Cost

@final
class EffectContext:

    def __init__(self, effect: 'Effect') -> None:
        self.effect = effect
        self.end_attack_messages: List['Message.AfterUnitAttackEnd'] = []
        self.end_thwart_messages: List['Message.AfterUnitThwartEnd'] = []
        self.initialized_targets: List[bool] = []
        self.paid_this_cost: 'Cost' = Cost("0")
        self.paid_this_resources: 'Resources' = Resources("0")
        self.chosen_cost_x: int|None = None
        self.targets_internal: List['CardFace'] = []
        # A card in the removed-from-game area may move only when the
        # resolving effect explicitly searched that area for that card.
        self.allowed_removed_cards: Set[Any] = set()

        self.bind_message: 'Message2|None' = None # 'self.ability.when', can only set None once, for "45078"

        self.is_must_choose = False
        self.only_work_when_no_other_options = False
        self.allow_partial_resolution = False
        self.play_initiation_checked = False
        self.play_initiation_allowed = False
        self.self_costs_prepared = False

        self.target_range: Tuple[int, int] = (0, 0)
        self.all_legal_targets: List['CardFace'] = []
        self.ignore_resource_cost: bool = False
        self.ask_player: 'Player|None' = None

        self.this_effect_need_cost: 'Cost|None' = None
        self.paid_this_res_effects: List['Effect'] = []

        # Spell effect
        self.initiator: User = self.effect.this.GetControlByOrOwner()

    def AddAtkMessage(self, end_message: 'Message.AfterUnitAttackEnd'):
        self.end_attack_messages.append(end_message)

    def AddThwMessage(self, end_message: 'Message.AfterUnitThwartEnd'):
        self.end_thwart_messages.append(end_message)

    def ResetBeforeOperation(self):
        self.end_attack_messages = []
        self.end_thwart_messages = []
        self.initialized_targets = [False, False, False]

    def GetTargetsInternal(self, index: int) -> List['CardFace']:
        assert index != 0
        assert self.initialized_targets[index] == False
        effect = self.effect
        initiator = effect.GetInitiator()
        # Fix "18004"
        labels: List['Ability.LABEL'] = [x for x in effect.ability.labels if x != 'defense']
        selector = effect.ability.selectors[index]
        self.initialized_targets[index] = True
        if selector != None:
            return initiator.AskChooseSelect(selector, effect, labels=labels, for_second_target=True)
        else:
            return []

    def ResetBeforeCondition(self):
        self.is_must_choose = False
        self.only_work_when_no_other_options = False
        self.allow_partial_resolution = False

    def ResetAfterOperation(self):
        # Before effect
        self.target_range = (0, 0)
        self.all_legal_targets = []
        self.ignore_resource_cost: bool = False
        self.ask_player: 'Player|None' = None

        self.this_effect_need_cost: 'Cost|None' = None
        self.chosen_cost_x = None
        self.paid_this_res_effects: List['Effect'] = []
        self.play_initiation_checked = False
        self.play_initiation_allowed = False
        self.self_costs_prepared = False
        self.allowed_removed_cards.clear()

        self.initiator: User = self.effect.this.GetControlByOrOwner()

        self.targets_internal: List['CardFace']
