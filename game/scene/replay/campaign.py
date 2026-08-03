from core import *
from game.game_run.game_challenge import GameChallenge

@dataclass
class CampaignDescriptor:
    version: str = field(default="")
    campaign_id: str = field(default="")
    name: str = field(default="")
    villain: List[str] = field(default_factory=lambda: [])
    expert: bool = field(default=False)
    # campaign: bool = field(default=False)
    challenges: List['GameChallenge.CHALLENGE'] = field(default_factory=lambda: [])
    # custom_script: str = field(default="")
    schemes: List[str] = field(default_factory=lambda: [])
    set_aside: List[str] = field(default_factory=lambda: [])
    encounters: List[str] = field(default_factory=lambda: [])
    encounter_sets: List[str] = field(default_factory=lambda: []) # "standard", "expert"
    modular_sets: List[str] = field(default_factory=lambda: []) # Only for json
    campaign_log: Dict[str, str] = field(default_factory=lambda: {})

    def UpdateVersion(self):
        pass

    def InferCampaignId(self) -> str:
        """Identify legacy campaign scenes that predate an explicit campaign id."""
        campaign_ids_by_prefix = {
            "04": "rise_of_red_skull",
            "16": "galaxys_most_wanted",
            "27": "sinister_motives",
            "32": "mutant_genesis",
            "40": "next_evolution",
            "45": "age_of_apocalypse",
            "50": "agents_of_shield",
        }
        for card_id in [*self.villain, *self.schemes, *self.encounters]:
            campaign_id = campaign_ids_by_prefix.get(card_id[:2])
            if campaign_id:
                self.campaign_id = campaign_id
                break
        return self.campaign_id

    def SetChallenge(self, *challenges: 'GameChallenge.CHALLENGE'):
        self.challenges = list(sorted(set(challenges)))
