from typing import Final
from core import *
from game.card.face import *
from game.effect import *
from game.deck import *

class SelectorEnd:
    def __init__(self,
                # Process rule
                peek: bool=False,
                not_move: bool=False,
                not_shuffle: bool=False,
                ):
        self.peek       = peek
        self.not_move   = not_move
        self.not_shuffle: Final = not_shuffle

    def Process(self, effect: 'Effect', targets: Sequence['CardFace']) -> bool:
        # Shuffle
        do_move = True
        if self.not_move:
            do_move = False
        if not self.not_shuffle:
            SelectorEnd.DoShuffle(effect, targets, do_move, False)
        elif do_move:
            SelectorEnd.DoMove(effect, targets, do_move)
        return True

    def OnSelectTargetFailure(self, effect: 'Effect', peeked_faces: Sequence['CardFace']) -> None:
        if self.peek and peeked_faces:
            SelectorEnd.DoShuffle(effect, peeked_faces, False, True)

    @staticmethod
    def DoMove(
            effect: 'Effect',
            faces: Sequence['CardFace'],
            need_move: bool,
            *,
            shuffle_origin_on_restore: bool=False,
            ) -> List['Deck']:
        from game.operate.faces import Faces

        places: List[Deck] = []
        moved_faces: List['CardFace'] = []

        for face in faces:
            deck = face.card.area
            if deck.flags.is_deck:
                if not face.card.IsFaceUp():
                    moved_faces.append(face)
                    places.append(face.card.area)

        if need_move:
            if moved_faces:
                Faces.MoveAllToProcessingArea(
                    moved_faces,
                    effect,
                    shuffle_origin_on_restore=shuffle_origin_on_restore,
                )
        else:
            # if moved_faces:
            #     CardFace.PeekCards(moved_faces, effect)
            pass

        return places

    @staticmethod
    def DoShuffle(effect: 'Effect', faces: Sequence['CardFace'], need_move: bool, is_failure: bool) -> None:
        from game.deck.deck import Deck

        places: List[Deck] = SelectorEnd.DoMove(
            effect,
            faces,
            need_move,
            shuffle_origin_on_restore=True,
        )

        if need_move or is_failure:
            for deck in Types.RemoveDuplicates(places):
                assert deck.GetSize() != 0
                if deck.GetSize() == 0:
                    # Send.AfterDeckRunOut(deck)
                    # deck.ShuffleWithDiscardPile(True, effect)
                    pass
                else:
                    deck.Shuffle(effect)
