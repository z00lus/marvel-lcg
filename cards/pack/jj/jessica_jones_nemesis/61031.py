from . import *


def GetAbilities() -> Sequence['Ability']:

    def highest_attack(effect: 'Effect', this: 'CardFace') -> int:
        values = [
            face.attack
            for face in Worlds.GetOnFieldCharacters(effect)
            if face != this and HasAttack.IsType(face)
        ]
        return max(values, default=0)

    def highest_scheme_or_thwart(effect: 'Effect', this: 'CardFace') -> int:
        values: List[int] = []
        for face in Worlds.GetOnFieldCharacters(effect):
            if face == this:
                continue
            if HasScheme.IsType(face):
                values.append(face.scheme)
            if HasThwart.IsType(face):
                values.append(face.thwart)
        return max(values, default=0)

    update_event = [
        OnEvent.CardKeyword(Unit2),
        OnEvent.Form(Identity),
    ]

    return [
        *AbilityFactory.GiveKeywordToInPlayWhenApplyThis(
            "This",
            get_new_value=highest_attack,
            base_atk=1,
            change_on_event=update_event,
        ),
        *AbilityFactory.GiveKeywordToInPlayWhenApplyThis(
            "This",
            get_new_value=highest_scheme_or_thwart,
            base_sch=1,
            change_on_event=update_event,
        ),
    ]
