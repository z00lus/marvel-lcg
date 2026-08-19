from . import *


def GetAbilities() -> Sequence['Ability']:
    return ArtAttachmentAbilities("G", stalwart=True)
