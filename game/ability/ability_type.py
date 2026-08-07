from enum import Enum
from typing import Final
from game.ability import *

"""
1. Constant abilities, keywords, and scheme icons.
2. Status cards.
3. "Forced Interrupt"
4. "Interrupt"
5. "Boost" "When Defeated" and "When Revealed"
6. "Forced Response"
7. "Response"
8. Consequential damage.
"""

class TimingPriority(Enum):
    Rule            = 0
    Statistics      = 1
    Constant        = 2
    Status          = 3
    ForcedInterrupt = 4
    Interrupt       = 5
    Boost           = 6
    ForcedResponse  = 7
    Response        = 8
    Normal          = 9
    Consequential   = 10
    End             = 11

class AbilityType(str, Enum):

    Rule            = "Rule"        # Ignore treat as blank, NoOutOfPlayLimit

    Temp0           = "Temp Fast"   # Ignore treat as blank
    Temp1           = "Temp Delay"  # Ignore treat as blank
    Temp2           = "Temp End"    # Ignore treat as blank

    Temp0UI         = "Temp Fast UI"

    Statistics          = "Statistics"
    Scenario            = "Scenario"
    Campaign            = "Campaign"
    NonKeyword          = "Constant"
    NonKeywordBold      = "ConstantBold"
    NonKeywordStar      = "ConstantStar"
    CheckResource       = "CheckResource"
    PlayTurnOption      = "Turn Option" # 'Change Form'
    BasicPower          = "Basic Power" # 'Recover', 'Attack', 'Thwart', 'Defense'
    Ask                 = "Ask"

    Resource            = "Resource"
    HeroResource        = "Hero Resource"
    AlterEgoResource    = "Alter-Ego Resource"

    Action              = "Action"
    ForcedAction        = "Forced Action" # the player phase cannot end until all possible forced actions among all players have been performed
    HeroAction          = "Hero Action" # 'Attack'
    AlterEgoAction      = "Alter-Ego Action"
    FirstPlayerAction   = "First Player Action"

    Setup               = "Setup"

    Interrupt           = "Interrupt"
    ForcedInterrupt     = "Forced Interrupt"
    ForcedInterruptHero = "Forced Interrupt (Hero)"
    HeroInterrupt       = "Hero Interrupt"
    AlterEgoInterrupt   = "Alter-Ego Interrupt"
    FirstPlayerInterrupt = "First Player Interrupt"

    Boost               = "Boost" # + Force
    WhenDefeated        = "When Defeated"
    WhenRevealed        = "When Revealed" # If is minion, then + Force
    WhenCompleted       = "When Complete"
    Preparation         = "Preparation"

    Response            = "Response"
    ForcedResponse      = "Forced Response"
    HeroResponse        = "Hero Response"
    AlterEgoResponse    = "Alter-Ego Response"

    Special             = "Special"

    DiscardForResource  = "Discard" # Discard this card to generate resource
    ChooseAbility       = "ChooseAbility"
    Status              = "Status"
    Consequential       = "Consequential"
    DelayAbility        = "Delay Ability"
    Challenge           = "Challenge"

    @property
    def flags(self):
        return {
            AbilityType.Rule                    : AbilityTypeFlags.Rule,
            AbilityType.Temp0                   : AbilityTypeFlags.Temp0,
            AbilityType.Temp0UI                 : AbilityTypeFlags.Temp0UI,
            AbilityType.Temp1                   : AbilityTypeFlags.Temp1,
            AbilityType.Temp2                   : AbilityTypeFlags.Temp2,
            AbilityType.Statistics              : AbilityTypeFlags.Statistics,
            AbilityType.Scenario                : AbilityTypeFlags.Scenario,
            AbilityType.Campaign                : AbilityTypeFlags.Campaign,
            AbilityType.NonKeyword              : AbilityTypeFlags.NonKeyword,
            AbilityType.NonKeywordBold          : AbilityTypeFlags.NonKeywordBold,
            AbilityType.NonKeywordStar          : AbilityTypeFlags.NonKeywordStar,
            AbilityType.CheckResource           : AbilityTypeFlags.CheckResource,
            AbilityType.PlayTurnOption          : AbilityTypeFlags.PlayTurnOption,
            AbilityType.BasicPower              : AbilityTypeFlags.BasicPower,
            AbilityType.Ask                     : AbilityTypeFlags.Ask,
            AbilityType.Resource                : AbilityTypeFlags.Resource,
            AbilityType.HeroResource            : AbilityTypeFlags.HeroResource,
            AbilityType.AlterEgoResource        : AbilityTypeFlags.AlterEgoResource,
            AbilityType.Action                  : AbilityTypeFlags.Action,
            AbilityType.ForcedAction            : AbilityTypeFlags.ForcedAction,
            AbilityType.HeroAction              : AbilityTypeFlags.HeroAction,
            AbilityType.AlterEgoAction          : AbilityTypeFlags.AlterEgoAction,
            AbilityType.FirstPlayerAction       : AbilityTypeFlags.FirstPlayerAction,
            AbilityType.Setup                   : AbilityTypeFlags.Setup,
            AbilityType.Interrupt               : AbilityTypeFlags.Interrupt,
            AbilityType.ForcedInterrupt         : AbilityTypeFlags.ForcedInterrupt,
            AbilityType.ForcedInterruptHero     : AbilityTypeFlags.ForcedInterruptHero,
            AbilityType.HeroInterrupt           : AbilityTypeFlags.HeroInterrupt,
            AbilityType.AlterEgoInterrupt       : AbilityTypeFlags.AlterEgoInterrupt,
            AbilityType.FirstPlayerInterrupt    : AbilityTypeFlags.FirstPlayerInterrupt,
            AbilityType.Boost                   : AbilityTypeFlags.Boost,
            AbilityType.WhenDefeated            : AbilityTypeFlags.WhenDefeated,
            AbilityType.WhenRevealed            : AbilityTypeFlags.WhenRevealed,
            AbilityType.WhenCompleted           : AbilityTypeFlags.WhenCompleted,
            AbilityType.Preparation             : AbilityTypeFlags.Preparation,
            AbilityType.Response                : AbilityTypeFlags.Response,
            AbilityType.ForcedResponse          : AbilityTypeFlags.ForcedResponse,
            AbilityType.HeroResponse            : AbilityTypeFlags.HeroResponse,
            AbilityType.AlterEgoResponse        : AbilityTypeFlags.AlterEgoResponse,
            AbilityType.Special                 : AbilityTypeFlags.Special,
            AbilityType.DiscardForResource      : AbilityTypeFlags.DiscardForResource,
            AbilityType.ChooseAbility           : AbilityTypeFlags.ChooseAbility,
            AbilityType.Status                  : AbilityTypeFlags.Status,
            AbilityType.Consequential           : AbilityTypeFlags.Consequential,
            AbilityType.DelayAbility            : AbilityTypeFlags.DelayAbility,
            AbilityType.Challenge               : AbilityTypeFlags.Challenge,
        }[self]

class AbilityTypeFlags:

    TYPE_PRIORITY: Final = {
        AbilityType.Rule:               TimingPriority.Rule,
        AbilityType.Challenge:          TimingPriority.Rule,
        AbilityType.Temp0:              TimingPriority.Rule,
        AbilityType.Temp0UI:            TimingPriority.Rule,
        AbilityType.Statistics:         TimingPriority.Statistics,
        AbilityType.Scenario:           TimingPriority.Rule,
        AbilityType.Campaign:           TimingPriority.Rule,
        AbilityType.NonKeyword:         TimingPriority.Constant,
        AbilityType.NonKeywordBold:     TimingPriority.Constant,
        AbilityType.NonKeywordStar:     TimingPriority.Constant,
        AbilityType.CheckResource:      TimingPriority.Constant,
        AbilityType.DelayAbility:       TimingPriority.Rule, # Fix "50068"
        AbilityType.ForcedInterrupt:    TimingPriority.ForcedInterrupt,
        AbilityType.ForcedInterruptHero:TimingPriority.ForcedInterrupt,
        AbilityType.Interrupt:          TimingPriority.Interrupt,
        AbilityType.HeroInterrupt:      TimingPriority.Interrupt,
        AbilityType.AlterEgoInterrupt:  TimingPriority.Interrupt,
        AbilityType.FirstPlayerInterrupt:TimingPriority.Interrupt,
        AbilityType.Boost:              TimingPriority.Boost,
        AbilityType.WhenRevealed:       TimingPriority.Boost,
        AbilityType.WhenDefeated:       TimingPriority.ForcedInterrupt,
        AbilityType.WhenCompleted:      TimingPriority.ForcedInterrupt,
        AbilityType.ForcedResponse:     TimingPriority.ForcedResponse,
        AbilityType.Response:           TimingPriority.Response,
        AbilityType.HeroResponse:       TimingPriority.Response,
        AbilityType.AlterEgoResponse:   TimingPriority.Response,
        AbilityType.Status:             TimingPriority.Status,
        AbilityType.Consequential:      TimingPriority.Consequential,
        AbilityType.Temp1:              TimingPriority.Normal,
        AbilityType.Temp2:              TimingPriority.End,
    }

    class Base:
        ui_display_name = False
        is_rule = False
        is_action = False
        is_forced_action = False
        is_discard_pay = False
        is_challenge = False
        is_interrupt = False
        is_response = False
        is_special = False
        is_basic_power = False
        is_play_turn_option = False
        is_ask = False
        is_resource = False
        is_when_reveal = False
        is_when_defeated = False
        is_when_completed = False
        is_boost = False
        is_nonkeyword = False
        is_choose_ability = False
        is_setup = False
        is_delay_ability = False
        is_check_pay = False
        is_status = False
        is_hero_type = False
        is_hero_action = False
        is_hero_response = False
        is_first_player_type = False
        is_alterego_type = False
        is_forced = False
        is_temp = False
        is_ignore_game_area = False
        is_rule = False
        is_statistics = False
        is_is_preparation = False
        need_render_ui = False

        ability_type: AbilityType

        # @property
        @classmethod
        def GetPriority(cls, rule: 'WorldRule|None'=None) -> 'TimingPriority':
            return AbilityTypeFlags.TYPE_PRIORITY.get(cls.ability_type, TimingPriority.Normal)

        @classmethod
        def IsType(cls, type: AbilityType) -> bool:
            return cls.ability_type == type

    class Rule(Base):
        ui_display_name = True
        is_rule = True
        is_forced = True
        is_ignore_game_area = True
        ability_type = AbilityType.Rule

    class Temp0(Base):
        is_forced = True
        is_temp = True
        is_ignore_game_area = True
        ability_type = AbilityType.Temp0

    class Temp0UI(Temp0):
        ui_display_name = True
        need_render_ui = True
        ability_type = AbilityType.Temp0UI

    class Temp1(Temp0):
        ability_type = AbilityType.Temp1

    class Temp2(Temp0):
        ability_type = AbilityType.Temp2

    class Statistics(Base):
        ui_display_name = True
        is_forced = True
        is_ignore_game_area = True
        is_rule = True
        is_statistics = True
        ability_type = AbilityType.Statistics

    class Scenario(Base):
        ui_display_name = True
        is_forced = True
        is_rule = True
        ability_type = AbilityType.Scenario

    class Campaign(Scenario):
        ability_type = AbilityType.Campaign

    class NonKeyword(Base):
        is_nonkeyword = True
        is_forced = True
        ability_type = AbilityType.NonKeyword

    class NonKeywordBold(NonKeyword):
        ability_type = AbilityType.NonKeywordBold

    class NonKeywordStar(NonKeyword):
        ability_type = AbilityType.NonKeywordStar

    class CheckResource(Base):
        is_check_pay = True
        is_forced = True
        ability_type = AbilityType.CheckResource

    class PlayTurnOption(Base):
        is_play_turn_option = True
        ability_type = AbilityType.PlayTurnOption

    class BasicPower(Base):
        is_basic_power = True
        ability_type = AbilityType.BasicPower

    class Ask(Base):
        is_ask = True
        ability_type = AbilityType.Ask

    class Resource(Base):
        is_resource = True
        ability_type = AbilityType.Resource

    class HeroResource(Resource):
        is_hero_type = True
        ability_type = AbilityType.HeroResource

    class AlterEgoResource(Resource):
        is_alterego_type = True
        ability_type = AbilityType.AlterEgoResource

    class Action(Base):
        ui_display_name = True
        is_action = True
        need_render_ui = True
        ability_type = AbilityType.Action

    class ForcedAction(Action):
        is_forced_action = True
        ability_type = AbilityType.ForcedAction

    class HeroAction(Action):
        is_hero_type = True
        is_hero_action = True
        ability_type = AbilityType.HeroAction

    class AlterEgoAction(Action):
        is_alterego_type = True
        ability_type = AbilityType.AlterEgoAction

    class FirstPlayerAction(Action):
        is_first_player_type = True
        ability_type = AbilityType.FirstPlayerAction

    class Setup(Base):
        is_setup = True
        is_forced = True
        need_render_ui = True
        ability_type = AbilityType.Setup

    class Interrupt(Base):
        ui_display_name = True
        is_interrupt = True
        need_render_ui = True
        ability_type = AbilityType.Interrupt

    class ForcedInterrupt(Interrupt):
        is_forced = True
        ability_type = AbilityType.ForcedInterrupt

    class ForcedInterruptHero(ForcedInterrupt):
        ability_type = AbilityType.ForcedInterruptHero

    class HeroInterrupt(Interrupt):
        is_hero_type = True
        ability_type = AbilityType.HeroInterrupt

    class AlterEgoInterrupt(Interrupt):
        is_alterego_type = True
        ability_type = AbilityType.AlterEgoInterrupt

    class FirstPlayerInterrupt(Interrupt):
        is_first_player_type = True
        ability_type = AbilityType.FirstPlayerInterrupt

    class Boost(Base):
        ui_display_name = True
        is_boost = True
        is_forced = True
        need_render_ui = True
        ability_type = AbilityType.Boost

    class WhenDefeated(Base):
        ui_display_name = True
        is_when_defeated = True
        is_forced = True
        need_render_ui = True
        ability_type = AbilityType.WhenDefeated

    class WhenRevealed(Base):
        ui_display_name = True
        is_when_reveal = True
        is_forced = True
        need_render_ui = True
        ability_type = AbilityType.WhenRevealed

    class WhenCompleted(Base):
        ui_display_name = True
        is_when_completed = True
        is_forced = True
        need_render_ui = True
        ability_type = AbilityType.WhenCompleted

    class Preparation(Base):
        ui_display_name = True
        is_forced = True
        is_preparation = True
        need_render_ui = True
        ability_type = AbilityType.Preparation

    class Response(Base):
        ui_display_name = True
        is_response = True
        need_render_ui = True
        ability_type = AbilityType.Response

    class ForcedResponse(Response):
        is_forced = True
        ability_type = AbilityType.ForcedResponse

    class HeroResponse(Response):
        is_hero_type = True
        is_hero_response = True
        ability_type = AbilityType.HeroResponse

    class AlterEgoResponse(Response):
        is_alterego_type = True
        ability_type = AbilityType.AlterEgoResponse

    class Special(Base):
        ui_display_name = True
        is_special = True
        is_forced = True
        need_render_ui = True
        ability_type = AbilityType.Special

    class DiscardForResource(Base):
        ui_display_name = True
        is_discard_pay = True
        ability_type = AbilityType.DiscardForResource

    class ChooseAbility(Base):
        is_choose_ability = True
        ability_type = AbilityType.ChooseAbility

    class Status(Base):
        is_status = True
        is_forced = True
        ability_type = AbilityType.Status

    class Consequential(Base):
        is_forced = True
        ability_type = AbilityType.Consequential

    class DelayAbility(Base):
        is_delay_ability = True
        is_forced = True
        is_ignore_game_area = True
        ability_type = AbilityType.DelayAbility

    class Challenge(Base):
        ui_display_name = True
        is_challenge = True
        is_forced = True
        ability_type = AbilityType.Challenge
