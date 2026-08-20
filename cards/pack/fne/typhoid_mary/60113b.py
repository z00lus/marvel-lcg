from . import *


def GetAbilities() -> Sequence['Ability']:
    def flip_to_trust(effect: 'Effect', player: 'Player') -> None:
        this = effect.this.CastTo(Attachment)
        if not this.IsInPlay():
            return
        this.card.Flip(effect, call_reveal=False)
        trust = this.card.face
        if EncounterSideScheme.IsType(trust):
            trust.PutIntoPlay(player, effect)
            trust.Reveal(player, effect)

    def damaged(effect: 'Effect', message: 'Message.AfterUnitTookDamage') -> None:
        # Mary Walker is attached to the scenario villain, so the damaged
        # enemy does not have a player controller.  The printed effect is
        # resolved by the first player instead.
        flip_to_trust(effect, Worlds.GetFirstPlayer(effect))

    def round_end(effect: 'Effect', message: 'Message.WhenRoundEnd') -> None:
        flip_to_trust(effect, Worlds.GetFirstPlayer(effect))

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(Villain),
        AbilityFactory.EnemyCannotActivate(
            AbilityType.NonKeyword,
            "AttachedEnemy",
        ),
        AbilityFactory.AfterUnitTookDamage(
            AbilityType.ForcedResponse,
            "AttachedEnemy",
            damaged,
        ),
        AbilityFactory.WhenRoundEnd(
            AbilityType.ForcedResponse,
            None,
            round_end,
        ),
    ]
