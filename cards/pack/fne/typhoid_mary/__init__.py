from cards.pack import *


TYPHOID_MARY = CardFinder(name="Typhoid Mary", card_type=Villain)
BLOODY_MARY = CardFinder(name="Bloody Mary", card_type=Villain)
MARY_WALKER = CardFinder(name="Mary Walker", card_type=Attachment)
DISTURBED_PSYCHE = CardFinder(name="Disturbed Psyche", card_type=Environment)


def IsActivatingMary(message: 'Message.WhenCardBecomeBoost', name: str) -> bool:
    return message.activating_enemy.IsName(name)


def CheckDisturbedPsycheVictory(effect: 'Effect') -> None:
    psyche = Worlds.FindCardOnField(effect, DISTURBED_PSYCHE)
    if psyche and psyche.GetCounters('damage') >= 3:
        Worlds.SetGameOver(True, effect)


def MaryDefeatReplacement(printed_hp: str) -> 'Ability':
    def replace_defeat(effect: 'Effect', message: 'Message.WhenUnitWouldBeDefeated') -> None:
        villain = message.trigger.CastTo(Villain)
        psyche = Worlds.FindCardOnField(effect, DISTURBED_PSYCHE)
        if not psyche:
            return
        message.SetBeInstead(effect)
        Faces.PlaceCountersOn([psyche], 1, 'damage', effect)
        villain.ResetHealth(effect, printed_hp)
        CheckDisturbedPsycheVictory(effect)

    return AbilityFactory.WhenUnitWouldBeDefeated(
        AbilityType.ForcedInterrupt,
        "This",
        replace_defeat,
    )


def FlipMaryWalkerToTrust(effect: 'Effect', player: 'Player') -> None:
    walker = Worlds.FindCardOnField(effect, MARY_WALKER)
    if not walker:
        return
    walker.card.Flip(effect, call_reveal=False)
    trust = walker.card.face
    if EncounterSideScheme.IsType(trust):
        trust.PutIntoPlay(player, effect)
        trust.Reveal(player, effect)
