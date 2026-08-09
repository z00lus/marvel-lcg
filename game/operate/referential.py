from cards.database import CardsDB
from . import *

@final
class Referential:
    @staticmethod
    def _IsEncounterCard(face: 'CardFace') -> bool:
        """Return whether ``face`` belongs to the encounter card class.

        A few scenario cards, including the Milano, use a player-card type so
        they can stay in a player's play area, but are explicitly printed with
        the Encounter class.  Referential targeting must classify those cards
        as encounter cards rather than ordinary player cards.
        """
        from game.card.face.base import ClassCard

        return EncounterCard.IsType(face) or \
            ClassCard.IsType(face) and face.IsClass("Encounter")

    @staticmethod
    def _IsPlayerCard(face: 'CardFace') -> bool:
        return PlayerCard.IsType(face) and \
            not Referential._IsEncounterCard(face)

    @staticmethod
    def _GetPlayers(world: 'World') -> Sequence['Player']:
        try:
            return world.const_players
        except (AttributeError, AssertionError):
            return getattr(world, "players", [])

    @staticmethod
    def _GetIdentity(player: 'Player') -> 'CardFace|None':
        try:
            return player.GetIdentity()
        except (AttributeError, AssertionError):
            return None

    @staticmethod
    def _IdentitySetMatches(identity_set: str, card_set: str) -> bool:
        if card_set.endswith(" Nemesis"):
            card_set = card_set[:-len(" Nemesis")]

        # The Miles Morales identity and nemesis set use different historical
        # spellings in the card database.
        aliases = {
            "Spider-Man - Miles Morales": "Spider-Man - Morales",
        }
        identity_set = aliases.get(identity_set, identity_set)
        card_set = aliases.get(card_set, card_set)
        return identity_set == card_set

    @staticmethod
    def _GetOriginalOwner(face: 'CardFace') -> 'Player|Scenario|None':
        try:
            return face.card.GetOriginalOwner()
        except AttributeError:
            return getattr(face.card, "owner_original", None)

    @staticmethod
    def GetAssociatedIdentity(face: 'CardFace', world: 'World') -> 'Player|None':
        """Return the player identity with which ``face`` is associated.

        Rules Reference 1.7 explicitly includes the identity card,
        identity-specific cards, obligations, nemesis cards, and cards in an
        identity side deck. Player ownership identifies identity-specific and
        side-deck cards; encounter-card association is derived from the
        obligation/nemesis metadata rather than a generic encounter-set match.
        """
        from game.card.face.base import ClassCard
        from game.card.face.card_type import Identity, Obligation

        players = Referential._GetPlayers(world)

        for player in players:
            identity = Referential._GetIdentity(player)
            if identity and face.card == identity.card:
                return player

            set_aside_obligations = getattr(player, "set_aside_obligations", [])
            if face.card in set_aside_obligations:
                return player

        if Identity.IsType(face) or \
            ClassCard.IsType(face) and face.IsClass("IdentitySpecific"):
            owner = Referential._GetOriginalOwner(face)
            if owner in players:
                return owner

        is_identity_encounter_card = Obligation.IsType(face) or \
            EncounterCard.IsType(face) and face.paper.set_name.endswith(" Nemesis")
        if not is_identity_encounter_card:
            return None

        for player in players:
            identity = Referential._GetIdentity(player)
            if identity and Referential._IdentitySetMatches(
                identity.paper.set_name,
                face.paper.set_name,
            ):
                return player
        return None

    @staticmethod
    def _MatchesReferencedName(find_names: Sequence[str], face: 'CardFace') -> bool:
        return any(face.IsName(name) or face.IsSubName(name) for name in find_names)

    @staticmethod
    def _GetFacesInGame(by_effect: 'Effect', extra_faces: Sequence['CardFace']) -> List['CardFace']:
        cards = getattr(getattr(by_effect.world, "object_manager", None), "card_dict", {})
        faces = [card.face for card in cards.values()]
        for face in [by_effect.this, *extra_faces]:
            if face not in faces:
                faces.append(face)
        return faces

    @staticmethod
    def _FilterV17OneName(find_name: str, legal_faces: List['CardFace'], by_effect: 'Effect') -> Sequence['CardFace']:
        this = by_effect.this
        faces_in_game = Referential._GetFacesInGame(by_effect, legal_faces)
        named_faces = [
            face for face in faces_in_game
            if Referential._MatchesReferencedName([find_name], face)
        ]

        # 1. The card on which the referential ability is printed.
        if any(face.card == this.card for face in named_faces):
            return [face for face in legal_faces if face.card == this.card]

        # 2. Cards associated with the same identity. This tier deliberately
        # does not include a generic "same encounter set" relationship.
        identity = Referential.GetAssociatedIdentity(this, by_effect.world)
        if identity != None:
            same_identity_faces = [
                face for face in named_faces
                if Referential.GetAssociatedIdentity(face, by_effect.world) == identity
            ]
            if same_identity_faces:
                return [face for face in legal_faces if face in same_identity_faces]

        # 3. Player cards for an ability on a player card, or encounter cards
        # for an ability on an encounter card. Never cross that boundary.
        if Referential._IsEncounterCard(this):
            return [
                face for face in legal_faces
                if Referential._IsEncounterCard(face)
            ]
        if Referential._IsPlayerCard(this):
            return [
                face for face in legal_faces
                if Referential._IsPlayerCard(face)
            ]
        return legal_faces

    @staticmethod
    def _FilterV17(find_names: Sequence[str], legal_faces: List['CardFace'], by_effect: 'Effect') -> Sequence['CardFace']:
        allowed_faces: List[CardFace] = []
        for find_name in find_names:
            for face in Referential._FilterV17OneName(find_name, legal_faces, by_effect):
                if Referential._MatchesReferencedName([find_name], face) and face not in allowed_faces:
                    allowed_faces.append(face)
        return allowed_faces

    @staticmethod
    def BelongToSameIdentityEncounterSet(find_names: List[str], face: 'CardFace', legal_faces: List['CardFace']) -> List['CardFace']:
        face.card.IsAsOtherCard()

        check_faces: List[CardFace] = []
        set_name = face.paper.set_name
        # Fix "50061"
        set_name_nemesis = set_name[:-8] if set_name.endswith(" Nemesis") else None
        set_id = face.paper.card_id[:2]

        if set_name == "Iceman" and set_name_nemesis == None:
            set_name_nemesis = "Frostbite"

        has_this_name_in_set = False
        for card_id in CardsDB.sets_cards[set_name]:
            if CardsDB.papers[card_id].name in find_names:
                has_this_name_in_set = True
                break
        if not has_this_name_in_set:
            return legal_faces

        for target in legal_faces:
            if target.paper.set_name == set_name or \
                target.paper.set_name == set_name_nemesis:
                # Hack "Magneto"
                if set_name == "Magneto" or \
                    set_name == "Venom":
                    if target.paper.card_id[:2] != set_id:
                        continue
                check_faces.append(target)
        if check_faces:
            return check_faces
        return []

    @staticmethod
    def Filter(finder: 'CardFinder|None', legal_faces: List['CardFace'], by_effect: 'Effect') -> Sequence['CardFace']:
        if not finder:
            return legal_faces

        check_by_name = finder.check_by_name
        if not check_by_name:
            return legal_faces

        return Referential._FilterV17(check_by_name, legal_faces, by_effect)

    @staticmethod
    def Check(finder: 'CardFinder', face: 'CardFace', from_effect: 'Effect') -> bool:
        if not finder.Check(face, from_effect):
            return False

        check_by_name = finder.check_by_name
        if not check_by_name:
            return True
        return face in Referential._FilterV17(
            check_by_name,
            [face],
            from_effect,
        )
