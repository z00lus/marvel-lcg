from . import *

class Token(Component):
    @override
    def __init__(self, card: 'Card') -> None:
        self.token: Dict['CardFace.TOKEN', int] = {}

        super().__init__(card)

    @override
    def OnParentReset(self):
        # Tokens belong to a card only while it remains in play. Reset is used
        # by the leave-play path, so every token type must return to the
        # shared supply rather than preserving non-threat token state.
        self.token = {}
        return super().OnParentReset()

    ################################################################################
    # Token
    def GetAllTokens(self) -> int:
        value = 0
        for key in self.token:
            value += self.token[key]
        return value
    def SetTokens(self, token: int, name: 'CardFace.TOKEN'):
        if name in self.token:
            self.token[name] = token
        else:
            self.token |= {name: token}
    def GetTokens(self, name: 'CardFace.TOKEN') -> int:
        if name in self.token:
            return self.token[name]
        else:
            return 0

    def PlaceTokens(self, token: int, name: 'CardFace.TOKEN') -> bool:
        self.SetTokens(token + self.GetTokens(name), name)
        return True
    def RemoveTokens(self, token: Literal["All"]|int, name: 'CardFace.TOKEN', forced: bool) -> bool:
        if name in self.token:
            if token == "All":
                self.token[name] = 0
                return True
            elif forced or self.token[name] >= token:
                self.token[name] -= token
                if self.token[name] < 0:
                    self.token[name] = 0
                return True
            return False
        else:
            return False

    def GetTokenNames(self) -> List['CardFace.TOKEN']:
        return list(self.token.keys())
