from core import *
from game.card.face import *
from game.deck import *
from game.ability import *
from game.message import *
from game.player import *
from cards.paper import Paper
from game.element.resources import Resources

@final
class Resource(ClassCard, FinalType):
    @override
    def __init__(self, paper: 'Paper') -> None:
        super().__init__(paper)

    @override
    def Play(self, player: 'Player', by_effect: 'Effect', message: 'Message2', resource: 'Resources', from_area: 'Deck', is_like_from_hand: bool):
        assert False, f"Resource cards can not be played, {self=}"

    @override
    def OnDealDamage(self, units: List['Unit2'], damage: 'int|DamageProperty', by_effect: 'Effect', *, property: 'AttackProperty|None'=None, attack_in_event: bool) -> int|None:
        identity = by_effect.GetInitiator().GetIdentity()
        if identity.IsDefeated():
            return None
        return identity.OnDealDamage(
            units,
            damage,
            by_effect,
            property=property,
            attack_in_event=attack_in_event,
        )

    @override
    def OnRemoveSchemeThreat(self, schemes: List['Scheme2'], value: int, by_effect: 'Effect') -> int|None:
        identity = by_effect.GetInitiator().GetIdentity()
        return identity.OnRemoveSchemeThreat(schemes, value, by_effect)
