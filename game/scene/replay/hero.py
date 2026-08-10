from core import *

@dataclass
class HeroDescriptor:
    version: str
    name: str
    hero: List[str]
    hero_deck: List[str]
    obligations: List[str]
    nemesis_set: List[str]
    player_deck: List[str] = field(default_factory=lambda: [])
    deck_name: str = field(default="")
    metadata: Dict[str, Any] = field(default_factory=lambda: {})

    def UpdateVersion(self):
        pass
