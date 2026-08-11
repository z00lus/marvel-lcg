from core import *

from game.game_run.game_challenge import GameChallenge

@dataclass
class NewGameDescriptor:
    campaign_json: str
    encounter_set_names: List[str]
    hero_json: List[str]
    seed: int
    timeout: float
    challenges: List['GameChallenge.CHALLENGE']
    rules: List[str]
    campaign_log: Dict[str, str]
    campaign_progress: Dict[str, Any] = field(default_factory=lambda: {})
    # custom_script: str = field(default="")
