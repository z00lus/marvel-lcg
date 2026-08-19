from . import *


def GetAbilities() -> Sequence['Ability']:

    def drang(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> None:
        this = effect.this.CastTo(Minion)
        player = message.GetAgainstPlayer()
        if not player:
            return
        Faces.PlaceCountersOn([this], 1, 'barrage', effect)
        player.GetIdentity().TakeIndirectDamage(
            this,
            this.GetCounters('barrage'),
            effect,
        )

    return [
        AbilityFactory.AfterUnitAttackYou(
            AbilityType.ForcedResponse,
            "This",
            drang,
        ),
    ]
