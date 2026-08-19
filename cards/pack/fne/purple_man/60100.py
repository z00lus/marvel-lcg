from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Attachment)
        player = message.GetToPlayer()
        ally = Filter.One(player.GetControlAllies(), effect, highest_cost=True)
        if ally:
            this.AttachTo2(ally, effect)
        else:
            ThisCardGainSurge(effect)

    return [
        AbilityFactory.TreatAttachedCardAsMinion(
            Ally,
            "Influenced Minion",
        ),
        AbilityFactory.WhenThisRevealed(None, revealed),
        PurpleManBoostAbility(),
    ]
