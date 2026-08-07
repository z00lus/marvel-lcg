from types import SimpleNamespace
import unittest
from unittest.mock import patch

# Match the application's normal import order without initializing the server.
from engine import Engine

from cards.database import CardsDB
from cards.paper import Paper
from game.card.card_finder import CardFinder
from game.card.face.card_type import Ally, Event, Hero, Minion, Obligation, Treachery, Upgrade
from game.operate.referential import Referential
from game.operate.worlds import Worlds


CARD_TYPES = {
    Ally: "Ally",
    Event: "Event",
    Hero: "Hero",
    Minion: "Minion",
    Obligation: "Obligation",
    Treachery: "Treachery",
    Upgrade: "Upgrade",
}


class FakeCard:
    def __init__(self, face, owner, game_area):
        self.face = face
        self.back_faces = []
        self.printed_faces = [face]
        self.owner_original = owner
        self.game_area = game_area
        face.card = self

    def GetOriginalOwner(self):
        return self.owner_original

    def GetGameArea(self):
        return self.game_area

    def IsAsOtherCard(self):
        return False


def MakeFace(
    face_type,
    name,
    *,
    card_id,
    set_name="",
    owner=None,
    card_class=None,
    game_area=None,
):
    desc = {}
    if face_type in (Ally, Event, Upgrade):
        desc["Class"] = card_class or "Basic"
    paper = Paper(
        card_id=card_id,
        pic_id="",
        type=CARD_TYPES[face_type],
        is_unique=False,
        name=name,
        subtitle="",
        desc=desc,
        traits=[],
        pack="test",
        set_name=set_name,
        text="",
    )
    face = face_type(paper)
    face.Initialize(1)
    FakeCard(face, owner, game_area)
    return face


def MakePlayer():
    player = SimpleNamespace(set_aside_obligations=[])
    player.GetIdentity = lambda: player.identity
    return player


def MakeEffect(source, faces, *, v17=True, v16=False, players=None):
    cards = {index: face.card for index, face in enumerate(faces)}
    world = SimpleNamespace(
        rule=SimpleNamespace(
            v17_referential_ability=v17,
            v16_referential_ability=v16,
        ),
        players=list(players or []),
        object_manager=SimpleNamespace(card_dict=cards),
    )
    return SimpleNamespace(this=source, world=world)


class ReferentialFilterV17Tests(unittest.TestCase):

    def test_self_referential_card_wins_the_first_tier(self):
        source = MakeFace(Event, "Echo", card_id="t001")
        other_echo = MakeFace(Ally, "Echo", card_id="t002")
        effect = MakeEffect(source, [source, other_echo])

        result = Referential.Filter(
            CardFinder(name="Echo"),
            [source, other_echo],
            effect,
        )

        self.assertEqual(result, [source])

    def test_same_identity_wins_over_unrelated_player_card(self):
        player = MakePlayer()
        identity = MakeFace(
            Hero,
            "Venom",
            card_id="t010",
            set_name="Venom",
            owner=player,
        )
        player.identity = identity
        source = MakeFace(
            Event,
            "Run and Gun",
            card_id="t011",
            set_name="Venom",
            owner=player,
            card_class="Hero",
        )
        unrelated_ally = MakeFace(
            Ally,
            "Venom",
            card_id="t012",
            owner=player,
            card_class="Justice",
        )
        effect = MakeEffect(
            source,
            [identity, source, unrelated_ally],
            players=[player],
        )

        result = Referential.Filter(
            CardFinder(name="Venom"),
            [identity, unrelated_ally],
            effect,
        )

        self.assertEqual(result, [identity])

    def test_identity_side_deck_card_is_in_the_same_identity_tier(self):
        player = MakePlayer()
        identity = MakeFace(
            Hero,
            "Storm",
            card_id="t020",
            set_name="Storm",
            owner=player,
        )
        player.identity = identity
        source = MakeFace(
            Event,
            "Weather Control",
            card_id="t021",
            set_name="Storm",
            owner=player,
            card_class="Hero",
        )
        weather = MakeFace(
            Upgrade,
            "Thunderstorm",
            card_id="t022",
            set_name="Weather",
            owner=player,
            card_class="Hero",
        )
        unrelated = MakeFace(
            Treachery,
            "Thunderstorm",
            card_id="t023",
            set_name="Weather Trap",
        )
        effect = MakeEffect(
            source,
            [identity, source, weather, unrelated],
            players=[player],
        )

        result = Referential.Filter(
            CardFinder(name="Thunderstorm"),
            [weather, unrelated],
            effect,
        )

        self.assertEqual(result, [weather])

    def test_identity_nemesis_card_is_in_the_same_identity_tier(self):
        player = MakePlayer()
        identity = MakeFace(
            Hero,
            "Iceman",
            card_id="t024",
            set_name="Iceman",
            owner=player,
        )
        player.identity = identity
        source = MakeFace(
            Event,
            "Face Your Nemesis",
            card_id="t025",
            set_name="Iceman",
            owner=player,
            card_class="Hero",
        )
        nemesis_pyro = MakeFace(
            Minion,
            "Pyro",
            card_id="t026",
            set_name="Iceman Nemesis",
        )
        scenario_pyro = MakeFace(
            Minion,
            "Pyro",
            card_id="t027",
            set_name="Brotherhood",
        )
        effect = MakeEffect(
            source,
            [identity, source, nemesis_pyro, scenario_pyro],
            players=[player],
        )

        result = Referential.Filter(
            CardFinder(name="Pyro"),
            [nemesis_pyro, scenario_pyro],
            effect,
        )

        self.assertEqual(result, [nemesis_pyro])

    def test_encounter_reference_can_cross_encounter_sets(self):
        source = MakeFace(
            Treachery,
            "Pyromaniac",
            card_id="t030",
            set_name="Mansion Attack",
        )
        brotherhood_pyro = MakeFace(
            Minion,
            "Pyro",
            card_id="t031",
            set_name="Brotherhood",
        )
        nemesis_pyro = MakeFace(
            Minion,
            "Pyro",
            card_id="t032",
            set_name="Iceman Nemesis",
        )
        effect = MakeEffect(source, [source, brotherhood_pyro, nemesis_pyro])

        result = Referential.Filter(
            CardFinder(name="Pyro"),
            [brotherhood_pyro, nemesis_pyro],
            effect,
        )

        self.assertEqual(result, [brotherhood_pyro, nemesis_pyro])

    def test_encounter_reference_does_not_cross_to_player_card(self):
        source = MakeFace(
            Treachery,
            "Call for Venom",
            card_id="t040",
            set_name="Scenario",
        )
        encounter_venom = MakeFace(
            Minion,
            "Venom",
            card_id="t041",
            set_name="Scenario",
        )
        player_venom = MakeFace(
            Ally,
            "Venom",
            card_id="t042",
            card_class="Justice",
        )
        effect = MakeEffect(source, [source, encounter_venom, player_venom])

        result = Referential.Filter(
            CardFinder(name="Venom"),
            [encounter_venom, player_venom],
            effect,
        )

        self.assertEqual(result, [encounter_venom])

    def test_player_reference_does_not_cross_to_encounter_card(self):
        source = MakeFace(Event, "Call for Venom", card_id="t050")
        player_venom = MakeFace(
            Ally,
            "Venom",
            card_id="t051",
            card_class="Justice",
        )
        encounter_venom = MakeFace(
            Minion,
            "Venom",
            card_id="t052",
            set_name="Scenario",
        )
        effect = MakeEffect(source, [source, player_venom, encounter_venom])

        result = Referential.Filter(
            CardFinder(name="Venom"),
            [player_venom, encounter_venom],
            effect,
        )

        self.assertEqual(result, [player_venom])

    def test_each_referenced_title_uses_its_own_priority(self):
        source = MakeFace(Event, "Alpha", card_id="t060")
        player_beta = MakeFace(
            Ally,
            "Beta",
            card_id="t061",
            card_class="Basic",
        )
        encounter_beta = MakeFace(
            Minion,
            "Beta",
            card_id="t062",
            set_name="Scenario",
        )
        effect = MakeEffect(source, [source, player_beta, encounter_beta])

        result = Referential.Filter(
            CardFinder(names=["Alpha", "Beta"]),
            [source, player_beta, encounter_beta],
            effect,
        )

        self.assertEqual(result, [source, player_beta])


class ReferentialConditionV17Tests(unittest.TestCase):

    def test_condition_check_uses_same_identity_priority(self):
        player = MakePlayer()
        identity = MakeFace(
            Hero,
            "Venom",
            card_id="t070",
            set_name="Venom",
            owner=player,
        )
        player.identity = identity
        source = MakeFace(
            Event,
            "Venom's Pistol",
            card_id="t071",
            set_name="Venom",
            owner=player,
            card_class="Hero",
        )
        unrelated_ally = MakeFace(
            Ally,
            "Venom",
            card_id="t072",
            card_class="Justice",
        )
        effect = MakeEffect(
            source,
            [identity, source, unrelated_ally],
            players=[player],
        )
        finder = CardFinder(name="Venom")

        self.assertTrue(Referential.Check(finder, identity, effect))
        self.assertFalse(Referential.Check(finder, unrelated_ally, effect))


class WorldsReferentialLookupTests(unittest.TestCase):

    def test_direct_named_lookup_uses_v17_encounter_class_filter(self):
        game_area = object()
        source = MakeFace(
            Treachery,
            "Call for Venom",
            card_id="t090",
            set_name="Scenario",
            game_area=game_area,
        )
        encounter_venom = MakeFace(
            Minion,
            "Venom",
            card_id="t091",
            set_name="Scenario",
            game_area=game_area,
        )
        player_venom = MakeFace(
            Ally,
            "Venom",
            card_id="t092",
            card_class="Justice",
            game_area=game_area,
        )
        effect = MakeEffect(source, [source, encounter_venom, player_venom])

        with patch.object(
            Worlds,
            "GetOnFieldCards",
            return_value=[encounter_venom, player_venom],
        ):
            result = Worlds.FindCardsOnField(effect, name="Venom")

        self.assertEqual(result, [encounter_venom])


if __name__ == "__main__":
    unittest.main()
