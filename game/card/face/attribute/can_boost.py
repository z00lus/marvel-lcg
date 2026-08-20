from . import *

# Gain boost card when activate
class CanBoost(CardFace):

    def GetBoostCardNum(self, message: 'Message2') -> int:
        assert False, f"You have to over write this function, {self=}"

    def GiveFacedownBoostCardsInternal(self, num: int, by_effect: 'Effect', would_atk_message: 'Message.WhenUnitWouldAttack|Message.WhenUnitWouldScheme|None'):
        from game.card.face.card_type import Minion
        from game.card.face.base import Villain

        def process(face: 'CardFace'):
            self.GiveBoostCard(face, by_effect, would_atk_message)

        from game.operate.worlds import Worlds
        Worlds.PopEncounterCards(num, process, True, by_effect)

        Message.AfterUnitGainFaceDownBoostCards_Text(self.card.CastTo(Minion|Villain), num, by_effect)

    def GiveBoostCard(self, face: 'CardFace', by_effect: 'Effect', would_atk_message: 'Message.WhenUnitWouldAttack|Message.WhenUnitWouldScheme|None'=None):
        from game.card.face.card_type import Minion
        from game.card.face.base import Villain

        would_message = Message.WhenEnemyWouldBeGivenBoostCard(
            self.card.CastTo(Minion|Villain),
            face,
            by_effect,
            would_atk_message,
        )
        would_message.Send()
        if would_message.is_be_instead:
            return False

        face.card.visible.Update()
        if not self.components.boostable.GiveBoostCard(face, by_effect):
            return False
        message = Message.AfterEnemyGivenBoostCard(self.card.CastTo(Minion|Villain), face, by_effect, would_atk_message)
        message.Send()
        return True

    def ResolveBoostCards(self, message: 'Message.WhenUnitBeingAttack|Message.WhenSchemeBeingScheme', call_back: Callable[['CardFace', int], None]) -> None:
        from game.message import Message
        from game.card.face.base import EncounterNonVillainCard
        from game.effect.rule import GameRule
        from game.operate.faces import Faces
        from game.operate.worlds import Worlds

        world = self.card.world
        while self.components.boostable.GetDeck().GetSize() != 0:
            face = self.components.boostable.GetDeck().GetTop()
            assert face

            if world.is_game_over:
                return

            # a. Flip the boost card faceup.
            would_flip_message = Message.WhenBoostCardWouldTurnedFaceUp(face, message)
            would_flip_message.Send()
            if would_flip_message.is_be_instead:
                continue

            # face.FlipTo(GameRule(face), face_up=True)

            Faces.MoveAllTo([face], world.area_boosting, GameRule(face))
            Message.AfterCardsMovedToBoostingArea_Text([face])

            if EncounterNonVillainCard.IsType(face) or face.effect.Find(type=AbilityType.WhenRevealed):
                # When a boost card is turned faceup during an enemy activation, add one additional boost icon to that card for each amplify icon in play.
                if EncounterNonVillainCard.IsType(face):
                    for amplify_face in Worlds.GetAmplifyFaces(self.card.game_area):
                        amplify_face.ResolveAmplify(face)

                flip_message = Message.WhenBoostCardTurnedFaceUp(face, message)
                flip_message.Send()

                # b.Resolve any “Boost” abilities, indicated by the star icon in the boost area. (All other abilities on the boost card are ignored.)
                become_message = Message.WhenCardBecomeBoost(face, flip_message)
                become_message.Send()

                # c. Increase the attacking enemy’s ATK value by one for each boost icon on the card.
                if EncounterNonVillainCard.IsType(face):
                    if flip_message.cancel_boost_icons:
                        boost_icons = 0
                    else:
                        boost_icons = face.CountBoostIconsInternal()
                    call_back(face, boost_icons)
                become_boost_message = Message.AfterCardBecomeBoost(face, become_message)
                become_boost_message.Send()
            # d. Discard the boost card.
            if face.card.area == world.area_boosting:
                Faces.DiscardAll([face], GameRule(face))
            if world.is_game_over:
                return
        assert self.components.boostable.GetDeck().GetSize() == 0, f"{self.components.boostable.GetDeck().Get()=}"
        return
