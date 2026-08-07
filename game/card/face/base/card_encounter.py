from game.card.face import *
from game.player import *

class EncounterCard(CanSurge, CanAccelerationToken, CardFace):
    pass

class EncounterNonVillainCard(HasBoostIcon, CanIncite, HasVictory, HasPeril, EncounterCard):

    def ResolveV17UniqueReveal(self, player: 'Player') -> bool:
        """Discard a matching revealed encounter card and deal its replacement."""
        if self.IsInPlay() or not self.card.world.IsThisUniqueInPlay(self):
            return False

        from game.effect.rule import UniqueEncounterCardRevealed
        from game.operate.faces import Faces

        rule = UniqueEncounterCardRevealed(self)
        discarded = Faces.DiscardAll([self], rule)
        if not discarded:
            # Permanent only prevents a card from leaving play. A matching
            # encounter card is still out of play in the revealing area.
            self.card.Discard(rule, ui_group=True, up_face=self)
        player.DealEncounterCards(1, rule)
        return True

    def IsNemesis(self, player: 'Player') -> bool:
        if not self.paper.set_name.endswith(" Nemesis"):
            return False
        identity = player.GetIdentity()
        from game.card.face.card_type import Minion
        if Minion.IsType(self):
            if not self.nemesis:
                return False
        # We cannot use this, see "01167" and "27058"
        #     return player.IsName(self.nemesis)
        if identity.paper.set_name == "Spider-Man - Miles Morales":
            return self.paper.set_name[:-8] == "Spider-Man - Morales"
        return identity.paper.set_name == self.paper.set_name[:-8]
