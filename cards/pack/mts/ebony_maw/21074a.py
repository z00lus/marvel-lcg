from . import *
from cards.pack.mts.campaign import CampaignSetup


def GetAbilities() -> Sequence['Ability']:
    return [
        *CampaignSetup(1),
    ]
