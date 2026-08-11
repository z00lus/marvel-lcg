from core import *
from game.scene import *
from game.scene.replay import *
from engine.lib import Json, Ver
from engine.file import FileManager

CATEGORY_NAME = "SCENE"

class UnsupportedReplayRulesError(ValueError):
    MESSAGE = (
        "This replay uses legacy rules and is not compatible with this "
        "Rules Reference 1.8-only branch."
    )

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)

class LoaderHelper:

    @staticmethod
    def NormalizeV18Rules(rules: List[str]) -> List[str]:
        version_names = {
            "v15_all", "v16_all", "v18_all",
            "v16_reveal", "v16_teamwork", "v16_player_elimination",
            "v16_referential_ability", "v16_confuse_stun",
            "v17_choice", "v17_ownership_control",
            "v17_referential_ability", "v17_uniqueness",
            "v17_actions_activations_costs",
            "v17_counters_modifiers_card_state",
            "v17_attacks_villain_transitions",
            "v17_setup_elimination_you",
            "v18_timing", "v18_surge", "v18_reveal", "v18_overkill",
            "v18_attacks", "v18_initiation", "v18_targeting",
            "v18_swaps", "v18_smaller_rules",
            "encounter_cards_ignore_crisis",
            "crisis_of_infinite_deadpools",
            "fix_surge",
        }
        normalized = [
            rule for rule in rules
            if rule not in version_names and
            not (rule.startswith("no_") and rule[3:] in version_names)
        ]
        normalized.append("v18_all")
        return list(sorted(set(normalized)))

    @staticmethod
    def EnsureSupportedReplay(scene: 'Scene') -> None:
        if "v18_all" not in scene.rules:
            raise UnsupportedReplayRulesError()

    @staticmethod
    def CreateScene(seed: int, campaign: CampaignDescriptor, players: Sequence[HeroDescriptor], rules: List[str]) -> 'Scene':
        scene = Scene(
            version=str(Ver.version),
            metadata={
                "seed": seed,
            },
            rules=LoaderHelper.NormalizeV18Rules(rules),
            campaign=campaign,
            players=players,
            inputs=[]
        )
        scene.UpdateVersion()
        for player in scene.players:
            assert player.name != ""
        return scene

    @staticmethod
    def Loads(file_path: str) -> 'Scene':
        # Log.Debug(f"File: {file_path}")

        scene = Json.LoadAs(file_path, Scene, check_sum="Warn")
        scene.UpdateVersion()

        scene.SetMetadataStr("path", file_path)

        return scene

class SceneLoader:

    ENCOUNTER_SET_FAMILIES = ("standard", "expert")

    @staticmethod
    def GetEncounterSetFamily(encounter_set: str) -> str|None:
        for family in SceneLoader.ENCOUNTER_SET_FAMILIES:
            if encounter_set == family or encounter_set.startswith(f"{family}_"):
                return family
        return None

    @staticmethod
    def MergeEncounterSets(required: Sequence[str], selected: Sequence[str]) -> List[str]:
        """Preserve required sets while replacing selected difficulty variants."""
        selected_by_family: Dict[str, str] = {}
        for encounter_set in selected:
            family = SceneLoader.GetEncounterSetFamily(encounter_set)
            if family:
                selected_by_family[family] = encounter_set

        merged: List[str] = []
        placed_families: Set[str] = set()

        def append_unique(encounter_set: str) -> None:
            if encounter_set not in merged:
                merged.append(encounter_set)

        for encounter_set in required:
            family = SceneLoader.GetEncounterSetFamily(encounter_set)
            if family and family in selected_by_family:
                if family not in placed_families:
                    append_unique(selected_by_family[family])
                    placed_families.add(family)
            else:
                append_unique(encounter_set)

        for encounter_set in selected:
            family = SceneLoader.GetEncounterSetFamily(encounter_set)
            if family:
                if family in placed_families:
                    continue
                if selected_by_family[family] != encounter_set:
                    continue
                placed_families.add(family)
            append_unique(encounter_set)

        return merged

    @staticmethod
    def NewFromJson(campaign_json: str, encounter_set_names: List[str]|None, hero_jsons: List[str], seed: int, rules: List[str], campaign_log: Dict[str, str]) -> 'Scene':
        players: List[HeroDescriptor] = []
        for hero_text in hero_jsons:
            player = Json.LoadsAs(hero_text, HeroDescriptor)
            player.UpdateVersion()
            players.append(player)

        campaign = Json.LoadsAs(campaign_json, CampaignDescriptor)
        campaign.UpdateVersion()

        if encounter_set_names != None:
            campaign.encounter_sets = SceneLoader.MergeEncounterSets(
                campaign.encounter_sets,
                encounter_set_names,
            )
        else:
            campaign.encounter_sets = SceneLoader.MergeEncounterSets(
                campaign.encounter_sets,
                campaign.modular_sets,
            )

        if campaign_log:
            campaign.campaign_log |= campaign_log

        scene = LoaderHelper.CreateScene(seed, campaign, players, rules)
        return scene

    @staticmethod
    def NewScene(campaign_name: str, encounter_set_names: List[str]|None, hero_names: List[str], seed: int) -> 'Scene':
        heroes_text: List[str] = []
        campaign_text: str = ""

        assert type(campaign_name) is str, f"{campaign_name=}"
        for hero_json in hero_names:
            file_path = FileManager.FindJsonPath('Hero', hero_json)
            assert file_path, f"{file_path=}"
            with FileManager.OpenFile(file_path, read=True) as file:
                heroes_text.append(file.Read())

        file_path = FileManager.FindJsonPath('Campaign', campaign_name)
        assert file_path, f"{file_path=}"
        with FileManager.OpenFile(file_path, read=True) as file:
            campaign_text = file.Read()

        scene = SceneLoader.NewFromJson(campaign_text, encounter_set_names, heroes_text, seed, [], {})
        return scene

    @staticmethod
    def Load(replay: str, nullable: bool=False) -> 'Scene|None':
        file_path = FileManager.FindJsonPath('Replay', replay, nullable=nullable)
        if file_path:
            scene = LoaderHelper.Loads(file_path)
            return scene
        else:
            return None
