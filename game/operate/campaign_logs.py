from typing import TypeAlias
from . import *

PLAYER_LIST_KEY: TypeAlias = Literal[
    "Obligations",
    "Rescued Allies",
    "Captive Allies",
    "Aspect Advantage: Reputation Track Reward",
]

PLAYER_STR_KEY: TypeAlias = Literal[
    "Tech Upgrade",
    "Basic Upgrade",
    "Role",
    "S.H.I.E.L.D. Tech: Reputation Track Reward",
    "Planning Ahead: Reputation Track Reward",
    "Campaign Ally",
    "Campaign Aspect Upgrade",
    "Campaign Aspect Support",
]

PLAYER_INT_KEY: TypeAlias = Literal[
    "Remaining hit points",
]

LOG_LIST_KEY: TypeAlias = Literal[
    "Experimental Weapons added to encounter deck",
    "Players engaged with minions",
    "Allies removed from the campaign",
    "Community Service: Victory for Scenarios #1-4",
    "Osborn Tech: Reputation Track Penalty",
    "Last Ones Standing: Victory for Scenario #4 - The Sinister Six",
    "Future Past Cards in Encounter Deck",
    "Future Past Cards removed from campaign",
    "Role Upgrades removed from campaign",
    "Marauders Defeated",
    "Campaign Environments Earned",
    "Mission Side Schemes Removed from campaign",
    "Mission Side Schemes Defeated",
    "Overseers Defeated",
]

LOG_INT_KEY: TypeAlias = Literal[
    "Number of delay counters on main scheme",
    "Reputation Track",
    "Waking Nightmare: Victory for Scenario #3 - Mysterio",
    "Morlocks Saved",
    "Scenario 3 Hope Summers Damage",
    "Scenario 4 Hope Summers Damage",
]

LOG_STR_KEY: TypeAlias = Literal[
    "",
    "Frightened Police Defeated",
    "Enemy of My Enemy Defeated",
    "Find the Prisoners Defeated",
    "Surprise Attack Defeated",
    "Jubilee",
    "Scenario 1 Player Side Scheme",
    "Scenario 2 Player Side Scheme",
    "Scenario 3 Player Side Scheme",
    "Scenario 4 Player Side Scheme",
    "Scenario 5 Player Side Scheme",
    "Scenario 4 Hope Damage Placement",
    "Scenario 5 Hope Damage Placement",
    "Age of Apocalypse Scenario",
    "Scenario 1 Mission Side Scheme",
    "Scenario 2 Mission Side Scheme",
    "Scenario 3 Mission Side Scheme",
    "Scenario 4 Mission Side Scheme",
    "Scenario 1 Overseer",
    "Scenario 2 Overseer",
    "Scenario 3 Overseer",
    "Scenario 4 Overseer",
    "Scenario 5 Overseer",
]

class CampaignLog:

    @staticmethod
    def GetStrInternal(key: str, by_effect: 'Effect') -> str:
        if Stores.HasKey(key, by_effect):
            return Stores.GetStr(key, by_effect)
        else:
            return ""

    @staticmethod
    def GetIntInternal(key: str, by_effect: 'Effect') -> int:
        value = CampaignLog.GetStrInternal(key, by_effect)
        if value:
            return int(value)
        return 0

    @staticmethod
    def GetListInternal(key: str, by_effect: 'Effect') -> List[str]:
        value = CampaignLog.GetStrInternal(key, by_effect)
        if value:
            return value.split(";")
        else:
            return []

    ################################################################################
    #
    @staticmethod
    def GetStr(key: LOG_STR_KEY, by_effect: 'Effect') -> str:
        return CampaignLog.GetStrInternal(key, by_effect)

    @staticmethod
    def GetInt(key: LOG_INT_KEY, by_effect: 'Effect') -> int:
        return CampaignLog.GetIntInternal(key, by_effect)

    @staticmethod
    def GetList(key: LOG_LIST_KEY, by_effect: 'Effect') -> List[str]:
        return CampaignLog.GetListInternal(key, by_effect)

    ################################################################################
    #
    @staticmethod
    def GetStrByPlayer(key: PLAYER_STR_KEY, player_id: Literal[0, 1, 2, 3], by_effect: 'Effect') -> str:
        player_keys = [f"Player {player_id+1} {key}", f"{key} P{player_id+1}"]
        for player_key in player_keys:
            value = CampaignLog.GetStrInternal(player_key, by_effect)
            if value:
                return value
        return ""

    @staticmethod
    def GetListByPlayer(key: PLAYER_LIST_KEY, player_id: Literal[0, 1, 2, 3], by_effect: 'Effect') -> List[str]:
        player_keys = [f"Player {player_id+1} {key}", f"{key} P{player_id+1}"]
        for player_key in player_keys:
            value = CampaignLog.GetListInternal(player_key, by_effect)
            if value:
                return value
        return []

    @staticmethod
    def GetIntByPlayer(key: PLAYER_INT_KEY, player_id: Literal[0, 1, 2, 3], by_effect: 'Effect') -> int:
        player_keys = [f"Player {player_id+1} {key}", f"{key} P{player_id+1}"]
        for player_key in player_keys:
            value = CampaignLog.GetIntInternal(player_key, by_effect)
            if value:
                return value
        return 0

    @staticmethod
    def SetStr(key: str, value: str, world: 'World'):
        world.store.SetStr(key, value)
