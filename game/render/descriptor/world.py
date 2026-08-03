from core import *
from game.render import *
from game.render.descriptor.card import CardDescriptor

@dataclass
class WorldDescriptor:
    # world
    render_id: int = field(default=0)
    round_id: int = field(default=0)
    phase: str = field(default='')
    prompt: str = field(default='')
    event_name: str = field(default='')
    prompt_last_text: str = field(default='')
    sound_name: str = field(default='')
    max_card_object_id: int = field(default=0)
    # play
    area_schemes_main: List[CardDescriptor] = field(default_factory=lambda: [])
    main_schemes_deck: List[CardDescriptor] = field(default_factory=lambda: [])
    area_schemes_side: List[CardDescriptor] = field(default_factory=lambda: [])
    additional_decks: List[Sequence[CardDescriptor]] = field(default_factory=lambda: [])
    additional_discard_piles: List[Sequence[CardDescriptor]] = field(default_factory=lambda: [])

    area_villain: List[CardDescriptor] = field(default_factory=lambda: [])
    villain_deck: List[CardDescriptor] = field(default_factory=lambda: [])
    encounter_deck: List[CardDescriptor] = field(default_factory=lambda: [])
    encounter_discard_pile: List[CardDescriptor] = field(default_factory=lambda: [])

    area_boost: List[CardDescriptor] = field(default_factory=lambda: [])
    area_environment: List[CardDescriptor] = field(default_factory=lambda: [])
    area_evidence: List[CardDescriptor] = field(default_factory=lambda: [])
    area_rule: List[CardDescriptor] = field(default_factory=lambda: [])
    area_mission: List[CardDescriptor] = field(default_factory=lambda: [])
    area_processing: List[CardDescriptor] = field(default_factory=lambda: [])
    area_revealing: List[CardDescriptor] = field(default_factory=lambda: [])
    area_resources: List[CardDescriptor] = field(default_factory=lambda: [])
    area_removed: List[CardDescriptor] = field(default_factory=lambda: [])
    area_insert: List[CardDescriptor] = field(default_factory=lambda: [])
    area_set_aside: List[CardDescriptor] = field(default_factory=lambda: [])
    victory_display: List[CardDescriptor] = field(default_factory=lambda: [])
    area_status_cards: List[CardDescriptor] = field(default_factory=lambda: [])
    # player
    @dataclass
    class PlayerDescriptor:
        area_hero: List[CardDescriptor] = field(default_factory=lambda: [])
        allies: List[CardDescriptor] = field(default_factory=lambda: [])
        supports: List[CardDescriptor] = field(default_factory=lambda: [])
        player_deck: List[CardDescriptor] = field(default_factory=lambda: [])
        player_discard_pile: List[CardDescriptor] = field(default_factory=lambda: [])
        dealt_encounter_cards: List[CardDescriptor] = field(default_factory=lambda: [])
        hand_cards: List[CardDescriptor] = field(default_factory=lambda: [])
        engaged_enemies: List[CardDescriptor] = field(default_factory=lambda: [])
        set_aside_nemesis_sets: List[CardDescriptor] = field(default_factory=lambda: [])
        set_aside_deck: List[CardDescriptor] = field(default_factory=lambda: [])

        additional_deck: List[CardDescriptor] = field(default_factory=lambda: [])
        additional_discard_pile: List[CardDescriptor] = field(default_factory=lambda: [])
        obligations_area: List[CardDescriptor] = field(default_factory=lambda: [])
        environment_area: List[CardDescriptor] = field(default_factory=lambda: [])

        resources: str = field(default='')
        is_eliminated: bool = field(default=False)
    players: List[PlayerDescriptor] = field(default_factory=lambda: [])
    # player_id: int = field(default=0)
    # Other
    active_card_ids: List[int] = field(default_factory=lambda: [])
