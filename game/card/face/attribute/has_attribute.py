from . import *

class HasAttribute(CardFace):

    def __init__(self, paper: 'Paper') -> None:
        self.attributes: Dict[str, Tuple[str|Callable[[str], None]|None, Type[int|str|bool]|None]] = {}
        self.non_numerical_attributes: Set['CardFace.KEY'] = set()
        self.player_num: int = 0
        self.info_dict: List[str] = []
        super().__init__(paper)

    def RegisterAttribute(self, key: CardFace.KEY, attr: str|Callable[[str], None]|None, t: Type[int|str|bool]=int):
        self.attributes |= {key: (attr, t)}

    def RegisterInfoDict(self, key: str):
        self.info_dict.append(key)

    def FormatPlayerNumValue(self, text: str) -> int:
        text = text.replace("*", f"*{self.player_num}")
        local_vars = {'val': 0}
        exec(f'val = int({text})', {}, local_vars)
        return local_vars['val']

    def SetPlayerNum(self, player_num: int):
        self.player_num = player_num
        self.info_dict.reverse() # Hack

    @final
    def InitPrintedValue(self, key: CardFace.KEY, value: str):
        if key == "Linked":
            # We process this in `create_linked_faces`
            return
        # A dash is an immutable non-numerical value.  It behaves as zero for
        # comparisons, but does not become a real zero that card effects can
        # increase through modifiers.
        if value in ["-", "–", "—"]:
            self.non_numerical_attributes.add(key)
            value = "0"
        attr = self.attributes[key]
        name, t = attr
        if name == None:
            pass
        elif isinstance(name, str):
            if t is int:
                format_value = self.FormatPlayerNumValue(value)
                setattr(self, name, format_value)
            elif t is bool:
                setattr(self, name, bool(int(value)))
            elif t is str:
                setattr(self, name, value)
            elif t is None:
                pass
            else:
                assert False, f"{self.paper.card_id}, {attr}"
        else:
            name(value)

    def CheckPrintedValue(self):
        pass

    @override
    def GetInfoDict(self) -> Dict[str, int]:
        dic: Dict[str, int] = {}
        for key in self.info_dict:
            value = getattr(self, key)
            if isinstance(value, str):
                value = 1 if value != "" else 0
            if isinstance(value, list):
                value = len(value) # type: ignore
            if value == None:
                value = 0
            dic |= {key: int(value)}
        return dic | super().GetInfoDict()
