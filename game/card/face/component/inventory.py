from . import *

class Inventory(Component):
    @override
    def __init__(self, card: 'Card') -> None:
        from game.deck import Deck2, DeckType
        super().__init__(card)
        # Attachment / Upgrade
        self.deck = Deck2(self.parent, DeckType.UpgradesArea, Asset2)
        # self.deck.bind_card = self.parent

    @override
    def OnParentLeavePlay(self, by_effect: 'Effect'):
        from game.operate.faces import Faces
        from game.card.face.attribute.has_permanent import HasPermanent

        super().OnParentLeavePlay(by_effect)
        faces = self.GetDeck().GetAll()
        former_host = self.parent.face
        ordinary_faces: List['CardFace'] = []
        for face in faces:
            if HasPermanent.IsType(face) and face.permanent:
                Faces.ResolvePermanentAttachmentAfterHostLeaves(
                    face,
                    former_host,
                    by_effect,
                )
            else:
                ordinary_faces.append(face)
        Faces.DiscardAll(ordinary_faces, by_effect)

    @override
    def OnBeforeParentFlip(self, by_effect: 'Effect', no_detach: bool=False):
        from game.operate.faces import Faces
        face = self.parent.face
        if self.parent.IsOnField():
            # If we call this, some ability +hp will lose
            # for upgrade in self.GetDeck().Get():
            #     upgrade.OnUnattachUpgrade(face, True)
            # face.LimitHealth(GameRule(face))
            for upgrade in self.deck.Get():
                # Fix "36038"
                if not (by_effect.this == upgrade and no_detach):
                    upgrade.OnDetachFrom(face, True)
        else:
            Faces.DiscardAll(self.deck.GetAll(), by_effect, simultaneous=True)
        return super().OnBeforeParentFlip(by_effect)

    @override
    def OnAfterParentFlip(self, by_effect: 'Effect'):
        from game.operate.faces import Faces
        face = self.parent.face
        if self.parent.IsOnField():
            # for upgrade in self.GetDeck().Get():
            #     upgrade.OnAttachUpgrade(face, True)
            # face.LimitHealth(GameRule(face), False)
            for upgrade in self.deck.Get():
                upgrade.OnAttachTo(face, True)
            pass
        else:
            Faces.DiscardAll(self.deck.GetAll(), by_effect, simultaneous=True)
        return super().OnAfterParentFlip(by_effect)

    @override
    def OnDiscard(self, by_effect: 'Effect') -> List['CardFace']:
        return self.deck.GetAll() + super().OnDiscard(by_effect)

    @override
    def OnRemove(self, by_effect: 'Effect'):
        from game.operate.faces import Faces

        Faces.DiscardAll(self.deck.GetAll(), by_effect)
        return super().OnRemove(by_effect)

    ################################################################################
    #
    def GetDeck(self) -> 'Deck2[Asset2]':
        return self.deck
