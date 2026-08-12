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
        # Search and play effects temporarily move cards to a processing area.
        # Keep the rules-level origin here so a failed "put into play" can
        # return the card to the game area it occupied before that UI move.
        self.processing_origins: Dict[Any, Tuple['Deck', int, bool]] = {}

        self.bind_message: 'Message2|None' = None # 'self.ability.when', can only set None once, for "45078"

        self.is_must_choose = False
        self.only_work_when_no_other_options = False
        self.allow_partial_resolution = False
        self.play_initiation_checked = False
        self.play_initiation_allowed = False
        # A played card is moved to the processing area before its RR 1.8
        # initiation checks.  Preserve the rules-level source area so cost
        # modifiers and "as if in hand" effects can still identify where the
        # declared card came from during those checks.
        self.declared_play_from_area: 'Deck|None' = None
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
        self.declared_play_from_area = None
        self.self_costs_prepared = False
        self.allowed_removed_cards.clear()
        self.processing_origins.clear()

        self.initiator: User = self.effect.this.GetControlByOrOwner()

        # A resolved choice effect is returned to its caller, which reads the
        # selected faces from ``effect.targets`` after resolution completes.
        # Keep those targets available here; the next target-selection pass
        # replaces them, while failed initiations clear them explicitly in
        # ResetFailedInitiation().

    def ResetFailedInitiation(self) -> None:
        """Discard every transient choice from an uncommitted initiation."""
        self.target_range = (0, 0)
        self.all_legal_targets = []
        self.targets_internal = []
        self.ignore_resource_cost = False
        self.ask_player = None
        self.this_effect_need_cost = None
        self.chosen_cost_x = None
        self.paid_this_res_effects = []
        self.paid_this_cost = Cost("0")
        self.paid_this_resources = Resources("0")
        self.play_initiation_checked = False
        self.play_initiation_allowed = False
        self.declared_play_from_area = None
        self.self_costs_prepared = False
        self.allowed_removed_cards.clear()
        self.processing_origins.clear()
        self.initiator = self.effect.this.GetControlByOrOwner()
