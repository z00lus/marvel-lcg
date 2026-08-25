from cards.pack import *


EVIDENCE_COUNTER = "evidence"


def FindAliasInvestigations(effect: 'Effect') -> 'Support|None':
    face = Worlds.FindCardOnField(effect, name="Alias Investigations", card_type=Support)
    if face:
        return face.CastTo(Support)
    return None


def PlaceEvidence(value: int, effect: 'Effect') -> int:
    alias = FindAliasInvestigations(effect)
    if not alias:
        return 0
    return Faces.PlaceCountersOn([alias], value, EVIDENCE_COUNTER, effect) or 0


def EvidenceCount(effect: 'Effect') -> int:
    alias = FindAliasInvestigations(effect)
    return alias.GetCounters(EVIDENCE_COUNTER) if alias else 0
