from build import Build
from engine.lib import *

CATEGORY_NAME = "VERSION"

class Ver:
    version: 'Ver'
    ui_version_str: str # only use for UI
    product_name: str
    release_label: str

    @staticmethod
    def Initialize():
        Ver.version = Ver(f'{Build.MAJOR}.{Build.MINOR}.{Build.PATCH}.{Build.BUILD}')
        Ver.ui_version_str = f"{Ver.version}{'r' if Build.release else 'd'}"
        Ver.product_name = Build.PRODUCT_NAME
        Ver.release_label = Build.RELEASE_LABEL

    # https://stackoverflow.com/questions/11887762/how-do-i-compare-version-numbers-in-python
    def __init__(self, ver: 'str|Ver') -> None:
        if not isinstance(ver, str):
            ver = str(ver)
        from packaging.version import Version
        self.ver = Version(ver)

    def __gt__(self, other: 'Ver') -> bool:
        return self.ver > other.ver
    def __ge__(self, other: 'Ver') -> bool:
        return self.ver >= other.ver
    def __lt__(self, other: 'Ver') -> bool:
        return self.ver < other.ver
    def __le__(self, other: 'Ver') -> bool:
        return self.ver <= other.ver
    def __eq__(self, other: object) -> bool:
        return type(other) is Ver and self.ver == other.ver

    def __repr__(self) -> str:
        return str(self.ver)

    ################################################################################
    #
    def VerifyVersion(self) -> None:
        from engine.log import Log

        support_version = Versions.last_support
        last_version = Ver.version

        infos = ""
        check_ver = self
        if support_version > check_ver:
            infos = f"Version {check_ver} is lower than support version {support_version}"
        elif last_version > check_ver:
            infos = f"Version {check_ver} is lower than last version {last_version}"
        assert check_ver >= support_version, f"{check_ver=} {support_version=}"
        if infos:
            Log.Warn(CATEGORY_NAME, infos)

    def CheckPuzzle(self):
        puzzle_ver = Versions.puzzle
        assert self >= puzzle_ver, f"{self=} {puzzle_ver=}"

    def IsFirstPlayerToken(self) -> bool:
        return self >= Versions.first_player_token

    def IsChecksum(self) -> bool:
        return self >= Versions.check_sum

    def IsCreateHeroDeckFirst(self):
        return self >= Versions.hero_deck_first

    def IsDeadpoolsEncounter(self):
        return self >= Versions.deadpools_encounter

    def IsFixTreachery(self):
        return self >= Versions.fix_treachery

class Versions:

    #                                           # After this version:
    last_support            = Ver(f'0.5.6.64')  # Begin support
    first_player_token      = Ver(f'0.5.7.134') # Place 'first player token'
    check_sum               = Ver(f'0.5.7.156') # Add crc
    metadata                = Ver(f'0.5.8.8')   # Use metadata in `Scene`
    hero_deck_first         = Ver(f'0.5.8.217') # Create hero deck first
    deadpools_encounter     = Ver(f'0.5.8.227') # Enable "1crisis_of_infinite_deadpools" by default
    fix_treachery           = Ver(f'0.5.9.148') # Enable "fix_treachery" by default
    puzzle                  = Ver(f'0.5.8')
