from cards.pack import *


PROTECTION_RACKET_SCHEMES = CardFinder(
    set_name="Protection Racket",
    card_type=MainScheme,
)


def PlaceThreatHere(effect: 'Effect', value: int=1) -> None:
    effect.this.CastTo(MainScheme).PlaceThreatOnSchemes([effect.this], value, effect)


def SelectProtectionRacketScheme(effect: 'Effect') -> None:
    """Resolve the printed solo setup choice for Protection Racket."""
    this = effect.this.CastTo(MainScheme)
    candidates = [this] + Worlds.MainSchemesDeck(effect).FindCards(
        PROTECTION_RACKET_SCHEMES,
    )
    if len(candidates) <= 1:
        return

    if Worlds.IsExpert(effect):
        chosen = Rand.RandomChoice(candidates, effect)
    else:
        chosen = Worlds.GetFirstPlayer(effect).AskChooseFace(
            candidates,
            effect,
            prompt="Choose your Protection Racket main scheme",
        )
    if not chosen:
        chosen = candidates[0]

    selected_current = chosen == this
    Faces.SetAside([candidate for candidate in candidates if candidate != chosen], effect)
    if chosen.paper.card_id.lower().endswith("a"):
        chosen.card.Flip(effect)
        chosen = chosen.card.face.CastTo(MainScheme)
    if not selected_current:
        chosen.PutIntoPlay("FirstPlayer", effect)


def SwapProtectionRacketScheme(effect: 'Effect') -> None:
    """Swap the active scheme with a random set-aside one and transfer threat."""
    current = Worlds.FindMainScheme(effect)
    candidates = Worlds.GetSetAsideAreaCards(effect, PROTECTION_RACKET_SCHEMES)
    if not current or not candidates:
        return

    chosen = Rand.RandomChoice(candidates, effect)
    threat = current.threat
    current.RemoveThreatInternal(effect.this, "All", effect)
    Faces.SetAside([current], effect)

    if chosen.paper.card_id.lower().endswith("a"):
        chosen.card.Flip(effect)
        chosen = chosen.card.face.CastTo(MainScheme)
    chosen.PutIntoPlay("FirstPlayer", effect)
    chosen.PlaceThreatOnSchemes([chosen], threat, effect)
