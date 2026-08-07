from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Match the application's normal import order without initializing the server.
from engine import Engine

from cards.paper import Paper
from game.card.face.base import Villain
from game.card.face.card_type import Ally, AlterEgo, Hero, Minion, Treachery, Upgrade
from game.operate.faces import Faces
from game.player.element.player_setup import PlayerSetup
from game.world.world_action import WorldAction


CARD_TYPES = {
    Ally: "Ally",
    AlterEgo: "AlterEgo",
    Hero: "Hero",
    Minion: "Minion",
    Treachery: "Treachery",
    Upgrade: "Upgrade",
    Villain: "Villain",
}


class FakeCard:
    def __init__(self, faces, world, *, game_area=None, in_play=False):
        self.face = faces[0]
        self.back_faces = list(faces[1:])
        self.printed_faces = list(faces)
        self.world = world
        self.game_area = game_area
        self.area = SimpleNamespace(
            flags=SimpleNamespace(is_in_play=in_play),
        )
        self.state = SimpleNamespace(is_defeating=False)
        for face in faces:
            face.card = self

    def IsApplyUniqueRule(self):
        return True

    def GetGameArea(self):
        return self.game_area

    def IsOnField(self):
        return self.area.flags.is_in_play


def MakeWorld(*, v17=True):
    return SimpleNamespace(
        rule=SimpleNamespace(v17_uniqueness=v17),
    )


def MakeFace(
    face_type,
    name,
    *,
    card_id,
    subtitle="",
    unique=True,
    world=None,
    game_area=None,
    in_play=False,
):
    desc = {}
    if face_type in (Ally, Upgrade):
        desc["Class"] = "Basic"
    paper = Paper(
        card_id=card_id,
        pic_id="",
        type=CARD_TYPES[face_type],
        is_unique=unique,
        name=name,
        subtitle=subtitle,
        desc=desc,
        traits=[],
        pack="test",
        set_name="Test",
        text="",
    )
    face = face_type(paper)
    face.Initialize(1)
    FakeCard(
        [face],
        world or MakeWorld(),
        game_area=game_area,
        in_play=in_play,
    )
    return face


def MakeIdentity(hero_name, alter_ego_name, *, card_id, world=None):
    world = world or MakeWorld()
    hero = Hero(Paper(
        card_id=f"{card_id}a",
        pic_id="",
        type="Hero",
        is_unique=True,
        name=hero_name,
        subtitle="",
        desc={},
        traits=[],
        pack="test",
        set_name=hero_name,
        text="",
    ))
    alter_ego = AlterEgo(Paper(
        card_id=f"{card_id}b",
        pic_id="",
        type="AlterEgo",
        is_unique=True,
        name=alter_ego_name,
        subtitle="",
        desc={},
        traits=[],
        pack="test",
        set_name=hero_name,
        text="",
    ))
    hero.Initialize(1)
    alter_ego.Initialize(1)
    FakeCard([hero, alter_ego], world)
    return hero


class V17UniqueMatchingTests(unittest.TestCase):

    def test_plain_unique_cards_with_the_same_title_match(self):
        first = MakeFace(Upgrade, "Jarnbjorn", card_id="u001")
        second = MakeFace(Upgrade, "Jarnbjorn", card_id="u002")

        self.assertTrue(first.MatchesV17Unique(second))
        self.assertFalse(first.CanCoexistWith(second))

    def test_plain_ally_and_minion_with_the_same_title_match(self):
        ally = MakeFace(Ally, "Jessica Jones", card_id="u010")
        minion = MakeFace(Minion, "Jessica Jones", card_id="u011")

        self.assertTrue(ally.MatchesV17Unique(minion))

    def test_alter_ego_title_matches_an_ally_title(self):
        identity = MakeIdentity("Black Panther", "T'Challa", card_id="u020")
        ally = MakeFace(Ally, "T'Challa", card_id="u021")

        self.assertTrue(identity.MatchesV17Unique(ally))
        self.assertFalse(identity.CanCoexistWith(ally))

    def test_alter_ego_title_matches_an_ally_subtitle(self):
        identity = MakeIdentity("Black Panther", "T'Challa", card_id="u030")
        ally = MakeFace(
            Ally,
            "Black Panther",
            subtitle="T'Challa",
            card_id="u031",
        )

        self.assertTrue(identity.MatchesV17Unique(ally))

    def test_same_moniker_with_different_people_can_coexist(self):
        peter = MakeFace(
            Ally,
            "Spider-Man",
            subtitle="Peter Parker",
            card_id="u040",
        )
        miles = MakeFace(
            Ally,
            "Spider-Man",
            subtitle="Miles Morales",
            card_id="u041",
        )

        self.assertFalse(peter.MatchesV17Unique(miles))
        self.assertTrue(peter.CanCoexistWith(miles))

    def test_matching_hero_titles_with_different_alter_egos_can_coexist(self):
        peter = MakeIdentity("Spider-Man", "Peter Parker", card_id="u050")
        miles = MakeIdentity("Spider-Man", "Miles Morales", card_id="u051")

        self.assertFalse(peter.MatchesV17Unique(miles))
        self.assertTrue(peter.CanCoexistWith(miles))

    def test_plain_title_does_not_match_subtitled_card_by_title_alone(self):
        plain = MakeFace(Ally, "Spider-Man", card_id="u060")
        peter = MakeFace(
            Ally,
            "Spider-Man",
            subtitle="Peter Parker",
            card_id="u061",
        )

        self.assertFalse(plain.MatchesV17Unique(peter))

class V17UniqueSetupTests(unittest.TestCase):

    def test_matching_identities_are_rejected_during_setup(self):
        world = MakeWorld()
        existing = MakeIdentity("Black Panther", "T'Challa", card_id="u080", world=world)
        incoming = MakeIdentity("T'Challa", "King of Wakanda", card_id="u081", world=world)
        existing_player = SimpleNamespace(
            area_hero=SimpleNamespace(GetAll=lambda: [existing]),
        )
        incoming_player = SimpleNamespace(
            world=SimpleNamespace(const_players=[existing_player]),
        )
        setup = PlayerSetup(incoming_player)

        with self.assertRaisesRegex(ValueError, "Matching identities"):
            setup.ValidateV17IdentitySelection(incoming)

    def test_different_people_using_the_same_moniker_are_allowed_in_setup(self):
        world = MakeWorld()
        peter = MakeIdentity("Spider-Man", "Peter Parker", card_id="u090", world=world)
        miles = MakeIdentity("Spider-Man", "Miles Morales", card_id="u091", world=world)
        existing_player = SimpleNamespace(
            area_hero=SimpleNamespace(GetAll=lambda: [peter]),
        )
        incoming_player = SimpleNamespace(
            world=SimpleNamespace(const_players=[existing_player]),
        )

        PlayerSetup(incoming_player).ValidateV17IdentitySelection(miles)

    def test_deck_validation_includes_the_identity(self):
        identity = MakeIdentity("Black Panther", "T'Challa", card_id="u100")
        matching_ally = MakeFace(Ally, "T'Challa", card_id="u101")
        setup = PlayerSetup(SimpleNamespace())

        with self.assertRaisesRegex(ValueError, "player deck"):
            setup.ValidateV17DeckUniqueness(identity, [matching_ally])

    def test_deck_validation_rejects_two_matching_unique_cards(self):
        identity = MakeIdentity("Captain Marvel", "Carol Danvers", card_id="u110")
        first = MakeFace(Upgrade, "Jarnbjorn", card_id="u111")
        second = MakeFace(Upgrade, "Jarnbjorn", card_id="u112")
        setup = PlayerSetup(SimpleNamespace())

        with self.assertRaisesRegex(ValueError, "Jarnbjorn"):
            setup.ValidateV17DeckUniqueness(identity, [first, second])


class V17UniqueRuntimeTests(unittest.TestCase):

    def test_matching_player_card_is_blocked_before_entering_play(self):
        game_area = object()
        world = MakeWorld()
        world.GetWorld = lambda: world
        identity = MakeIdentity("Black Panther", "T'Challa", card_id="u115", world=world)
        identity.card.game_area = game_area
        ally = MakeFace(
            Ally,
            "T'Challa",
            card_id="u116",
            world=world,
            game_area=game_area,
        )

        with patch("game.operate.worlds.Worlds.GetOnFieldCards", return_value=[identity]):
            self.assertTrue(WorldAction.IsThisUniqueInPlay(world, ally))

    def test_villain_is_allowed_to_enter_against_a_matching_identity(self):
        game_area = object()
        world = MakeWorld()
        world.GetWorld = lambda: world
        villain = MakeFace(
            Villain,
            "Venom",
            card_id="u120",
            world=world,
            game_area=game_area,
        )

        self.assertFalse(WorldAction.IsThisUniqueInPlay(world, villain))

    def test_generic_non_villain_reveal_discards_and_deals_replacement(self):
        world = MakeWorld()
        world.IsThisUniqueInPlay = Mock(return_value=True)
        treachery = MakeFace(
            Treachery,
            "Identity Crisis",
            card_id="u130",
            world=world,
        )
        player = Mock()
        rule = object()

        with patch("game.effect.rule.UniqueEncounterCardRevealed", return_value=rule), \
            patch.object(Faces, "DiscardAll", return_value=[treachery]) as discard:
            handled = treachery.ResolveV17UniqueReveal(player)

        self.assertTrue(handled)
        discard.assert_called_once_with([treachery], rule)
        player.DealEncounterCards.assert_called_once_with(1, rule)

if __name__ == "__main__":
    unittest.main()
