from core import *
from game.card.face import *
from game.ability import *
from game.card.face.model.base import ModelBase

class ModelName(ModelBase):

    def SetName(self, printed_name: str):
        def extract_prefix(input_string: str):
            import re
            # Define the regex patterns with capturing groups
            patterns = [
                r"(.*) - \d?[A-F]$",
                r"(.*) \d?[A-F]$",      # The Injured Senator 2A
                r"(.*) \([^()]+\)$"     # Kang (The Conqueror)
            ]
            
            # Iterate through the patterns and try to match
            for pattern in patterns:
                match = re.match(pattern, input_string)
                if match:
                    return match.group(1)
                    
            # If no pattern matches, return the original string or handle as needed
            return input_string

        self.name = extract_prefix(printed_name)
        self.printed_name = printed_name

    def SetSubtitle(self, printed_subtitle: str):
        self.printed_subtitle = printed_subtitle

    @final
    def IsName(self, name: str, check_cosider_as: bool=True, check_all_face: bool=False) -> bool:
        this = self.GetThis()
        if check_all_face:
            faces = [this] + this.card.back_faces
            for face in faces:
                if face and face.IsName(name, check_cosider_as):
                    return True
            return False
        else:
            if name == this.printed_name:
                return True
            if name == this.name:
                return True
            if name == "Ronan" and this.printed_name == "Ronan the Accuser":
                return True
            if this.IsCardId(name):
                return True
            if check_cosider_as and this.IsConsiderAs(name=name):
                return True
            return False

    ################################################################################
    #
    @final
    def IsUnique(self) -> bool:
        this = self.GetThis()
        return this.paper.is_unique

    @final
    def IsCardId(self, name: str) -> bool:
        this = self.GetThis()
        return name == this.paper.card_id

    @final
    def IsSubName(self, subname: str) -> bool:
        this = self.GetThis()
        return this.paper.subtitle == subname

    @final
    def TitleContain(self, title_contain: str) -> bool:
        this = self.GetThis()
        for name in [this.name] + [x for x in this.consider_as.names]:
            if title_contain in name:
                return True
        return False

    # If two identities share the same title, but each has a different alter-ego, they may coexist in play
    # If two unique allies share the same title, but each has a different subtitle, they may coexist in a player’s deck and in play.
    # If a hero and a unique ally share the same title, but the alter-ego and the subtitle are different, they may coexist in deckbuilding and in play.
    @final
    def GetV17UniqueTitles(self) -> Set[str]:
        from game.card.face.card_type import Identity
        from game.card.face.card_type import Hero

        this = self.GetThis()
        if not Identity.IsType(this):
            return {this.name}
        return {
            face.name
            for face in [this] + this.card.back_faces
            if Hero.IsType(face)
        }

    @final
    def GetV17UniqueAliases(self) -> Set[str]:
        from game.card.face.card_type import Identity
        from game.card.face.card_type import AlterEgo

        this = self.GetThis()
        if not Identity.IsType(this):
            return {this.printed_subtitle} if this.printed_subtitle else set()
        return {
            face.name
            for face in [this] + this.card.back_faces
            if AlterEgo.IsType(face)
        }

    @final
    def MatchesV17Unique(self, that: 'CardFace') -> bool:
        """Return whether two unique cards match under Rules Reference 1.7."""
        this = self.GetThis()
        if this.card == that.card:
            return False
        if not this.IsUnique() or not that.IsUnique():
            return False

        this_titles = this.GetV17UniqueTitles()
        that_titles = that.GetV17UniqueTitles()
        this_aliases = this.GetV17UniqueAliases()
        that_aliases = that.GetV17UniqueAliases()

        # Plain titles match only when neither card has a subtitle or an
        # alter-ego title.
        if not this_aliases and not that_aliases and this_titles & that_titles:
            return True

        # Otherwise, a subtitle/alter-ego title on either card must match any
        # title, subtitle, or alter-ego title on the other card.
        return bool(
            this_aliases & (that_titles | that_aliases) or
            that_aliases & (this_titles | this_aliases)
        )

    @final
    def CanCoexistWith(self, that: 'CardFace') -> bool:
        from game.card.face.card_type import Identity
        from game.card.face.card_type import Hero
        from game.card.face.card_type import AlterEgo

        this = self.GetThis()

        if not that.IsUnique():
            return True
        if not this.IsUnique():
            return True
        if this == that:
            return True

        if not this.card.IsApplyUniqueRule():
            return True
        if not that.card.IsApplyUniqueRule():
            return True

        return not this.MatchesV17Unique(that)

    ################################################################################
    #
    @final
    def GetDisplayName(self, *, no_hidden: bool=False, no_object_id: bool=False) -> str:
        this = self.GetThis()
        if no_object_id:
            object_id = 0
        else:
            object_id = '{:02}'.format(this.card.object_id)

        if this.card.IsAsOtherCard():
            id = f"({object_id},{this.paper.card_id},{this.card.printed_faces[0].paper.card_id}) "
        else:
            id = f"({object_id},{this.paper.card_id}) "

        hidden = ''
        if not no_hidden and not this.card.IsVisible("Any"):
            hidden = ' ?'
        return "[{}{}{}]".format(id, self.name, hidden)
