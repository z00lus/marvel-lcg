from . import *
from typing import Final


def GetEffectActivationText(effect: 'Effect', face: 'CardFace') -> 'TransText':
    if effect.ability.name == "Retaliate":
        from game.card.face.attribute.can_retaliate import CanRetaliate
        retaliate = face.CastTo(CanRetaliate).retaliate
        return TransText(
            "{face} retaliates for {damage} damage",
            face=face,
            damage=retaliate,
        )

    if effect.targets:
        return TransText(
            "{face} activates, targets {targets}",
            face=face,
            targets=effect.targets,
        )
    return TransText("{face} activates", face=face)


class SenderEffect:

    class WhenEffectWouldResolve(TriggerFaceMessage, TriggerNonePlayerMessage, CanBeInstead, CanGainValueMessage, HasEndEventMessage):
        def __init__(self, effect: 'Effect', message: 'Message2|None', by_effect: 'Effect', to_player: 'Player|None', control_by: 'Player|Scenario|None') -> None:
            from game.message import Message
            from game.card.face.base import EncounterCard
            self.effect: Final = effect
            face = effect.this
            self.by_effect: Final = by_effect
            self.control_by: Final = control_by # Fix "08001a" "08009"
            self.message: Final = message # None may mean `ResolveWhenRevealAbility`
            # if effect.ability.type in [AbilityType.HeroAction, AbilityType.AlterEgoAction, AbilityType.Action, AbilityType.Response, AbilityType.ForcedResponse, AbilityType.HeroResponse, AbilityType.WhenComplete, AbilityType.WhenRevealed, AbilityType.WhenDefeated, AbilityType.HeroInterrupt, AbilityType.AlterEgoInterrupt, AbilityType.AlterEgoResponse, AbilityType.Interrupt, AbilityType.ForcedInterrupt, AbilityType.Setup, ]:
            # if effect.ability.type in [AbilityType.HeroAction, AbilityType.AlterEgoAction, AbilityType.Action, AbilityType.Response, AbilityType.ForcedResponse, AbilityType.HeroResponse, AbilityType.WhenCompleted, AbilityType.WhenRevealed, AbilityType.WhenDefeated, AbilityType.AlterEgoResponse, AbilityType.Setup, AbilityType.Boost, ]:

            # Fix "45005"
            player = to_player if to_player != None else effect.initiator
            if not player.IsPlayer():
                # Fix "41018"
                if EncounterCard.IsType(face) and isinstance(message, TriggerNonePlayerMessage):
                    player = message.to_player
                else:
                    player = None

            super().__init__(trigger=face, player=player, end_event=Message.AfterEffectResolved)

            if effect.ability.flags.need_render_ui:
                text = GetEffectActivationText(effect, face)
                self.Present(text, "activate", face, *effect.targets)

    class AfterEffectResolved(TriggerFaceMessage, TriggerNonePlayerMessage, HasPreEventMessage):
        def __init__(self, effect: 'Effect', message: 'Message2|None', resolve_message: 'Message.WhenEffectWouldResolve') -> None:
            self.effect: Final = effect
            self.by_effect: Final = resolve_message.by_effect
            self.control_by: Final = resolve_message.control_by
            face = effect.this

            self.message: Final = message
            player = resolve_message.to_player

            super().__init__(trigger=face, player=player, pre_message=resolve_message)

        @property
        def when_resolve_message(self) -> 'Message.WhenEffectWouldResolve':
            return self.pre_message

    # class AfterCardRegisterEffects_Text(TextMessage):
    #     def __init__(self, face: 'CardFace', effects: Sequence['Effect']) -> None:
    #         # text = TransText("{card} lost effect {effects}")
    #         # self.Present(text, effects[0].this)
    #         pass

    class WhenSurgeWouldBeResolved(TriggerPlayerMessage, TriggerFaceMessage, CanBeInstead):
        def __init__(self, face: 'CanSurge', player: 'Player') -> None:
            super().__init__(player=player, trigger=face)
            text = TransText("{face} would surge against {player}", face=face, player=player)
            self.Present(text, "activate", face, player.GetIdentity())
