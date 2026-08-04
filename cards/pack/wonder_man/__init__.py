from cards.pack import *


def FindIonicPhysiology(effect: 'Effect') -> 'Upgrade|None':
    faces = effect.GetInitiator().GetControlUpgrade(
        CardFinder(name="Ionic Physiology", card_type=Upgrade)
    )
    return faces[0].CastTo(Upgrade) if faces else None


def GetIonicCards(effect: 'Effect') -> List['CardFace']:
    physiology = FindIonicPhysiology(effect)
    return physiology.GetPlacedCardArea().GetAll() if physiology else []


def GetEnergyCardsInDiscard(effect: 'Effect', *, include_resources: bool=False) -> List['CardFace']:
    card_type = Event|Resource if include_resources else Event
    return effect.GetInitiator().discard_pile.FindCards(
        CardFinder(card_type=card_type, has_printed_res="Y")
    )


def TuckUnderIonic(effect: 'Effect', faces: Sequence['CardFace']) -> bool:
    physiology = FindIonicPhysiology(effect)
    if not physiology:
        return False
    slots = max(0, 3 - physiology.GetPlacedCardArea().GetSize())
    chosen = list(faces)[:slots]
    return bool(chosen) and physiology.TuckCardUnderHere(chosen, effect)


def EnergyOverpaid(effect: 'Effect', maximum: int) -> int:
    return min(
        maximum,
        max(0, effect.GetCostX()),
        effect.GetPaidResources().GetColor("Y"),
    )
