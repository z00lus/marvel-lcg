from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.UnitCannotTakeDamageWhile(
            AbilityType.NonKeyword,
            Villain,
            while_face_is_in_play=CardFinder(
                name="Jackknifed Tanker Truck",
                card_type=SchemeSide2,
            ),
        ),
    ]
