from core import *
from game.card.face import *

@dataclass
class Paper:
    card_id: str
    pic_id: str
    type: str
    is_unique: bool
    name: str
    subtitle: str = field(default='')
    desc: Dict["CardFace.KEY", str] = field(default_factory=lambda: {})
    traits: List["CardFace.TRAITS"] = field(default_factory=lambda: [])
    pack: str = field(default='')
    set_name: "CardFace.SETNAMES" = field(default="")
    text: str = field(default='')

    @staticmethod
    def GetCardId(card_paper: Dict[str, Any]) -> str:
        return card_paper["card_id"]

    @staticmethod
    def GetFullLink(card_paper: Dict[str, Any]) -> str:
        if "full_link" in  card_paper:
            return card_paper["full_link"]
        else:
            return ""

    @staticmethod
    def GetAbilityLink(card_paper: Dict[str, Any]) -> str:
        if "ability_link" in  card_paper:
            return card_paper["ability_link"]
        else:
            return ""

    @staticmethod
    def Load(card_paper: Dict[str, Any], pack: str) -> 'Paper':
        card_id = card_paper["card_id"]
        pic_id = ""
        if "pic_id" in card_paper:
            pic_id = card_paper["pic_id"]
            from engine.file import Cache
            Cache.SetLinkPic(card_id, pic_id)
        type_name = card_paper["type"]
        unique = str(card_paper["name"]).startswith("* ")
        name = str(card_paper["name"]).lstrip("* ")

        if type_name == "Challenge":
            subtitle = ""
            desc: Dict["CardFace.KEY", str] = {}
            traits: List["CardFace.TRAITS"] = []
            set_name = ""
            text = card_paper["text"]
        else:
            subtitle = card_paper["subtitle"]
            desc = card_paper["desc"]
            traits = card_paper["traits"]
            set_name = card_paper["set_name"]

            if "text" in  card_paper:
                text = card_paper["text"]
            else:
                text = ""

        return Paper(
            card_id, pic_id, type_name, unique, name, subtitle, desc, traits, pack, set_name, text
        )

    def IsFromSet(self, set_name: "CardFace.SETNAMES") -> bool:
        return self.set_name == set_name

    def GetEncounterSetIdentity(self) -> Tuple[str, str]:
        """Return the encounter-set identity represented by its printed icon.

        The data source does not expose a separate icon identifier.  A set
        name is only unique within its product, so the pack/name pair is the
        stable identity used whenever sets themselves (rather than cards) are
        compared.
        """
        return self.pack, self.set_name

    def GetType(self) -> Type['Insert|Challenge|Hero|AlterEgo|Ally|Minion|EncounterVillain|Leader|MainScheme|SchemeSide2|PlayerSideScheme|Upgrade|Support|Attachment|Environment|Event|Obligation|Treachery|Resource|StatusCard|Evidence']:
        from game.card.face.card_type import Insert, Challenge
        from game.card.face.card_type import Minion
        from game.card.face.card_type import EncounterVillain
        from game.card.face.card_type import Leader
        from game.card.face.card_type import EncounterSideScheme
        from game.card.face.card_type import MainScheme
        from game.card.face.card_type import PlayerSideScheme
        from game.card.face.card_type import Upgrade
        from game.card.face.card_type import Support
        from game.card.face.card_type import Attachment
        from game.card.face.card_type import Environment
        from game.card.face.card_type import Obligation
        from game.card.face.card_type import Treachery
        from game.card.face.card_type import Ally
        from game.card.face.card_type import Hero
        from game.card.face.card_type import AlterEgo
        from game.card.face.card_type import Event
        from game.card.face.card_type import Resource
        from game.card.face.card_type import StatusCard
        from game.card.face.card_type import Evidence

        return {
            'Insert': Insert,
            'Challenge': Challenge,
            'Hero': Hero,
            'AlterEgo': AlterEgo,
            'Ally': Ally,
            'Minion': Minion,
            'Villain': EncounterVillain,
            'Leader': Leader,
            'MainScheme': MainScheme,
            'SideScheme': EncounterSideScheme,
            'PlayerSideScheme': PlayerSideScheme,
            'Upgrade': Upgrade,
            'Support': Support,
            'Attachment': Attachment,
            'Environment': Environment,
            'Event': Event,
            'Obligation': Obligation,
            'Treachery': Treachery,
            'Resource': Resource,
            'Status': StatusCard,
            'Evidence': Evidence,
        }[self.type]
