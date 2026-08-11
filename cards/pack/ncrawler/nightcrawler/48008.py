from . import *

# Teleport Drop

def GetAbilities() -> Sequence['Ability']:

    def teleport_drop(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        this.DealDamage(effect.targets, 8, effect)
        Faces.GiveStatus(effect.targets, "Stunned", effect)

    def get_bamf_cost(effect: 'Effect') -> Sequence['CardFace']:
        if not effect.targets:
            return []
        bamf = effect.targets[0].GetInventoryDeck().FindCard(name="Bamf!")
        return [bamf] if bamf else []

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            teleport_drop
        ).SetPlay().SetLabel('attack')
        .SetCostFunc(CostFunc.Discard(
            Select.From(get_bamf_cost, range=(1, 1)),
        ))
        .SetTarget(Enemy, with_attach=CardFinder(name="Bamf!")),
    ]
