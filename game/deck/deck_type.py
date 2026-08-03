from enum import Enum

class DeckTypeFlags:
    class Base:
        is_in_play = False
        is_deck = False
        is_discards = False
        is_out_of_play = False
        is_processing = False
        is_revealing = False
        is_in_hand = False
        is_player_deck = False
        is_encounter_deck = False
        is_encounter_discard_pile = False
        is_main_scheme_deck = False
        is_status_area = False
        is_engaged = False
        is_upgrades = False
        is_like_in_hand = False
        is_place_card_area = False
        is_dealt_encounter = False
        is_boost_area = False
        is_resources_area = False
        is_villain_area = False
        is_obligations_area = False
        is_victory_display = False
        is_removed = False
        is_set_aside = False
        is_face_up = False
        is_attach_boost_area = False
        is_side_scheme_area = False

    class PlaceCardArea(Base):
        is_out_of_play = True
        is_place_card_area = True # tuck area

    class UpgradesArea(Base):
        is_in_play = True
        is_upgrades = True
        is_face_up = True

    class PlayerDeck(Base):
        is_deck = True
        is_player_deck = True

    class DiscardPile(Base):
        is_deck = True
        is_discards = True
        is_face_up = True

    class AlliesArea(Base):
        is_in_play = True
        is_face_up = True

    class SupportsArea(Base):
        is_in_play = True
        is_face_up = True

    class HandsArea(Base):
        is_in_hand = True

    class EngagedEnemiesArea(Base):
        is_in_play = True
        is_engaged = True
        is_face_up = True

    class DealtEncounterCardsDeck(Base):
        is_dealt_encounter = True

    class HeroArea(Base):
        is_in_play = True
        is_face_up = True

    class ResourcesArea(Base):
        is_out_of_play = True
        is_resources_area = True
        is_face_up = True

    class AdditionalDeck(Base):
        is_deck = True
        is_out_of_play = True
        is_set_aside = True

    class AdditionalDiscardPile(Base):
        is_deck = True
        is_discards = True
        is_out_of_play = True
        is_set_aside = True
        is_face_up = True

    class AsideDeck(Base):
        is_out_of_play = True
        is_removed = True
        is_set_aside = True
        is_face_up = True

    class ObligationsArea(Base):
        is_in_play = True
        is_obligations_area = True
        is_face_up = True
        # is_out_of_play = True

    class EncounterDeck(Base):
        is_deck = True
        is_encounter_deck = True

    class EncounterDiscardPile(Base):
        is_deck = True
        is_discards = True
        is_encounter_discard_pile = True
        is_face_up = True

    class MainSchemesArea(Base):
        is_in_play = True
        is_face_up = True

    class MainSchemesDeck(Base):
        is_out_of_play = True
        is_main_scheme_deck = True
        is_removed = True

    class SideSchemesArea(Base):
        is_in_play = True
        is_face_up = True
        is_side_scheme_area = True

    class VillainArea(Base):
        is_in_play = True
        is_villain_area = True
        is_face_up = True

    class VillainDeck(Base):
        is_out_of_play = True
        is_removed = True

    class BoostingArea(Base):
        is_out_of_play = True
        is_boost_area = True
        is_face_up = True

    class BoostCardsDeck(Base):
        is_attach_boost_area = True
        is_out_of_play = True

    class EnvironmentArea(Base):
        is_in_play = True
        is_face_up = True

    class EvidenceArea(Base):
        is_in_play = True
        is_face_up = True

    class RuleArea(Base):
        is_in_play = True
        is_face_up = True

    class MissionArea(Base):
        is_in_play = True
        is_face_up = True

    class ProcessingArea(Base):
        is_out_of_play = True
        is_processing = True
        is_face_up = True

    class RevealingArea(Base):
        is_out_of_play = True
        is_processing = True
        is_face_up = True
        is_revealing = True

    class RemovedArea(Base):
        is_out_of_play = True
        is_removed = True

    class VictoryDisplay(Base):
        is_out_of_play = True
        is_victory_display = True
        is_removed = True
        is_face_up = True

    class StatusArea(Base):
        is_status_area = True
        is_removed = True
        is_face_up = True


class DeckType(Enum):
    # Card
    PlaceCardArea           = 1 # Tuck under
    # Unit
    UpgradesArea            = 2
    BoostCardsDeck          = 3
    # Player
    PlayerDeck              = 10
    DiscardPile             = 11
    AlliesArea              = 12
    SupportsArea            = 13
    HandsArea               = 14
    EngagedEnemiesArea      = 15
    DealtEncounterCardsDeck = 16
    HeroArea                = 17
    ResourcesArea           = 18

    AdditionalDeck          = 20
    AdditionalDiscardPile   = 21
    AsideDeck               = 22
    ObligationsArea         = 23
    # World
    EncounterDeck           = 30
    EncounterDiscardPile    = 31
    MainSchemesArea         = 32
    MainSchemesDeck         = 33
    SideSchemesArea         = 34
    VillainArea             = 35
    VillainDeck             = 36
    BoostingArea            = 37 # Bind to world, like processing
    EnvironmentArea         = 38
    EvidenceArea            = 39
    ProcessingArea          = 40
    RevealingArea           = 41

    RemovedArea             = 51
    VictoryDisplay          = 52
    StatusArea              = 53
    RuleArea                = 54
    MissionArea             = 55

    @property
    def flags(self):
        return {
                DeckType.PlaceCardArea:             DeckTypeFlags.PlaceCardArea,
                DeckType.UpgradesArea:              DeckTypeFlags.UpgradesArea,
                DeckType.PlayerDeck:                DeckTypeFlags.PlayerDeck,
                DeckType.DiscardPile:               DeckTypeFlags.DiscardPile,
                DeckType.AlliesArea:                DeckTypeFlags.AlliesArea,
                DeckType.SupportsArea:              DeckTypeFlags.SupportsArea,
                DeckType.HandsArea:                 DeckTypeFlags.HandsArea,
                DeckType.EngagedEnemiesArea:        DeckTypeFlags.EngagedEnemiesArea,
                DeckType.DealtEncounterCardsDeck:   DeckTypeFlags.DealtEncounterCardsDeck,
                DeckType.HeroArea:                  DeckTypeFlags.HeroArea,
                DeckType.ResourcesArea:             DeckTypeFlags.ResourcesArea,
                DeckType.AdditionalDeck:            DeckTypeFlags.AdditionalDeck,
                DeckType.AdditionalDiscardPile:     DeckTypeFlags.AdditionalDiscardPile,
                DeckType.AsideDeck:                 DeckTypeFlags.AsideDeck,
                DeckType.ObligationsArea:           DeckTypeFlags.ObligationsArea,
                DeckType.EncounterDeck:             DeckTypeFlags.EncounterDeck,
                DeckType.EncounterDiscardPile:      DeckTypeFlags.EncounterDiscardPile,
                DeckType.MainSchemesArea:           DeckTypeFlags.MainSchemesArea,
                DeckType.MainSchemesDeck:           DeckTypeFlags.MainSchemesDeck,
                DeckType.SideSchemesArea:           DeckTypeFlags.SideSchemesArea,
                DeckType.VillainArea:               DeckTypeFlags.VillainArea,
                DeckType.VillainDeck:               DeckTypeFlags.VillainDeck,
                DeckType.BoostingArea:              DeckTypeFlags.BoostingArea,
                DeckType.BoostCardsDeck:            DeckTypeFlags.BoostCardsDeck,
                DeckType.EnvironmentArea:           DeckTypeFlags.EnvironmentArea,
                DeckType.EvidenceArea:              DeckTypeFlags.EvidenceArea,
                DeckType.RuleArea:                  DeckTypeFlags.RuleArea,
                DeckType.MissionArea:               DeckTypeFlags.MissionArea,
                DeckType.ProcessingArea:            DeckTypeFlags.ProcessingArea,
                DeckType.RevealingArea:             DeckTypeFlags.RevealingArea,
                DeckType.RemovedArea:               DeckTypeFlags.RemovedArea,
                DeckType.VictoryDisplay:            DeckTypeFlags.VictoryDisplay,
                DeckType.StatusArea:                DeckTypeFlags.StatusArea,
        }[self]

    # @property
    # def is_in_play(self) -> bool:
    #     return self.flags.is_in_play
    # @property
    # def is_deck(self) -> bool:
    #     return self.flags.is_deck
    # @property
    # def is_discards(self) -> bool:
    #     return self.flags.is_discards
    # @property
    # def is_out_of_play(self) -> bool:
    #     return self.flags.is_out_of_play

    # @property
    # def is_processing(self) -> bool:
    #     return self == DeckType.ProcessingArea
    # @property
    # def is_peek(self) -> bool:
    #     return self == DeckType.PeekArea
    # @property
    # def is_in_hand(self) -> bool:
    #     return self == DeckType.HandsArea
    # @property
    # def is_player_deck(self) -> bool:
    #     return self == DeckType.PlayerDeck
    # @property
    # def is_encounter_deck(self) -> bool:
    #     return self == DeckType.EncounterDeck
    # @property
    # def is_encounter_discard_pile(self) -> bool:
    #     return self == DeckType.EncounterDiscardPile
    # @property
    # def is_main_scheme_deck(self) -> bool:
    #     return self == DeckType.MainSchemesDeck
    # @property
    # def is_status_area(self) -> bool:
    #     return self == DeckType.StatusArea
    # @property
    # def is_engaged(self) -> bool:
    #     return self == DeckType.EngagedEnemiesArea
    # @property
    # def is_upgrades(self) -> bool:
    #     return self == DeckType.UpgradesArea
    # @property
    # def is_place_card(self) -> bool:
    #     return self == DeckType.PlaceCardArea
    # @property
    # def is_dealt_encounter(self) -> bool:
    #     return self == DeckType.DealtEncounterCardsDeck
    # @property
    # def is_boost_area(self) -> bool:
    #     return self == DeckType.BoostArea
    # @property
    # def is_resources_area(self)-> bool:
    #     return self == DeckType.ResourcesArea
    # @property
    # def is_villain_area(self) -> bool:
    #     return self == DeckType.VillainArea
    # @property
    # def is_obligations_area(self) -> bool:
    #     return self == DeckType.ObligationsArea
    # @property
    # def is_victory_display(self) -> bool:
    #     return self == DeckType.VictoryDisplay
    # @property
    # def is_removed(self) -> bool:
    #     return self in [DeckType.AsideDeck, DeckType.MainSchemesDeck, DeckType.VillainDeck, DeckType.RemovedArea, DeckType.VictoryDisplay, DeckType.StatusArea]
    # @property
    # def is_set_aside(self) -> bool:
    #     return self in [DeckType.AsideDeck, DeckType.AdditionalDeck, DeckType.AdditionalDiscardPile]
