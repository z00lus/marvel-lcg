from core import *
from game.card.face import *
from game.ability import *
from game.ability.factory import *
from game.message import *
from game.player import *
from game.deck import *
from game.card.face.model.base import ModelBase
from game.element.damage_property import DamageProperty
from game.world.game_area import *

# Actions
class ModelOnEvent(ModelBase):

    ################################################################################
    # For `Card` use

    # Call when not in play -> play
    def OnWouldEnterPlay(self, into_area: 'Deck') -> bool:
        # this = self.GetThis()
        # this.card.components.OnWouldEnterPlay()
        return True

    def OnWhenCardWouldMoveToArea(self, message: 'Message.WhenCardWouldMoveToArea') -> bool:
        message.Send()
        return not message.cannot

    # Call when in play -> not in play
    def OnWhenCardWouldLeavePlay(self, message: 'Message.WhenCardWouldLeavePlay') -> bool:
        message.Send()
        return not message.is_be_instead

    def OnWhenCardLeavePlay(self, message: 'Message.WhenCardLeavePlay') -> bool:
        message.Send()
        return True

    def OnLeavedPlayEnd(self, by_effect: 'Effect'):
        pass

    def OnAfterCardLeavePlay(self, message: 'Message.AfterCardLeavePlay') -> None:
        from game.effect.rule import GameRule
        this = self.GetThis()
        rule = GameRule(this)
        this.card.components.OnAfterLeavePlay(rule)
        message.Send()

    def OnWhenCardWouldDiscard(self, message: 'Message.WhenCardWouldDiscard') -> bool:
        message.Send()
        return True

    def OnAfterDestroy(self):
        pass

    def OnBeforeFlip(self, by_effect: 'Effect', no_detach: bool=False):
        this = self.GetThis()
        this.card.components.OnBeforeFlip(by_effect, no_detach)

    # Call when in play -> in play
    def OnFlip(self, by_effect: 'Effect', origin_face: 'CardFace|None'):
        this = self.GetThis()
        this.card.ui.ResetEffectedBy()
        this.ResetKeywords()
        this.OnResetModel()
        # this.card.components.OnFlip(by_effect, origin_face)

    def OnAfterFlip(self, by_effect: 'Effect', call_reveal: bool=False):
        from game.effect.rule import GameRule
        from game.card.face.base import EncounterCard
        from game.card.face.card_type import MainScheme
        from game.card.face.base import Villain
        this = self.GetThis()

        this.card.components.OnAfterFlip(by_effect)
        if this.IsInPlay():
            this.ApplyAfterEnterPlay(this.card.area, this.card.area, GameRule(this), is_flip=True)
            # Hack, fix "01114" "01127"
            this.card.state.is_swapping_end = False
            if this.IsFaceUp() and \
                (
                    EncounterCard.IsType(this) or \
                    MainScheme.IsType(this) or \
                    Villain.IsType(this)
                ) and \
                call_reveal:
                this.Reveal(None, GameRule(this), is_by_flipping=True)
        pass

    def OnWhenCardFlip(self, message: 'Message.WhenCardFlip') -> None:
        message.Send()

    def OnAfterCardFlip(self, message: 'Message.AfterCardFlip') -> None:
        message.Send()

    ################################################################################
    #
    def OnDealDamage(self, units: List['Unit2'], damage: 'int|DamageProperty', by_effect: 'Effect', *, property: 'AttackProperty|None'=None, attack_in_event: bool) -> int|None:
        assert property == None
        assert attack_in_event == False
        this = self.GetThis()
        # Fix "27131", "16062b"
        return this.DefaultDealDamageTo(this, units, damage, by_effect)

    def OnRemoveSchemeThreat(self, schemes: List['Scheme2'], value: int, by_effect: 'Effect') -> int|None:
        # assert False, f"You need to override this function, {self=}"
        this = self.GetThis()
        return this.DefaultRemoveSchemeThreat(this, schemes, value, by_effect)

    ################################################################################
    #
    def OnResetKeywords(self, by_effect: 'Effect'):
        this = self.GetThis()
        message = Message.WhenCardResetKeyword(this)
        message.Send()

    ################################################################################
    #
    def OnLeaveGameArea(self, game_area: 'GameArea'):
        pass

    def OnEnterGameArea(self, game_area: 'GameArea'):
        this = self.GetThis()
        message = Message.GameAreaAddCard(this)
        message.Send()

    ################################################################################

    ################################################################################
    #
    def OnWhenCardSetup(self, message: 'Message.WhenCardSetup') -> None:
        message.Send()

    @final
    def Setup(self, before_put_setup_cards: bool) -> bool:
        from game.message import Message
        this = self.GetThis()
        message = Message.WhenCardSetup(this, before_put_setup_cards)
        self.OnWhenCardSetup(message)
        return True

    ################################################################################
    #
    def OnReset(self, message: 'Message.WhenCardReset_Text') -> None:
        message.Send()

    # This will not reset health
    @final
    def Reset(self, is_flip: bool) -> bool:
        from game.message import Message
        this = self.GetThis()
        message = Message.WhenCardReset_Text(this, is_flip)
        this.card.ui.ResetEffectedBy()
        this.ResetKeywords()
        this.OnResetModel()
        if not is_flip:
            this.card.components.OnReset()
        this.OnReset(message)
        return True

    ################################################################################
    #
    def OnPutIntoPlay(self, message: 'Message.WhenCardPutIntoPlay') -> bool:
        message.Send()
        return True

    def OnAfterCardPutIntoPlay(self, message: 'Message.AfterCardPutIntoPlay') -> 'None':
        message.Send()

    @final
    # Will auto engage if this is a Minion
    def PutIntoPlay(self, player: 'Player|Literal["CurrentPlayer", "FirstPlayer"]', by_effect: 'Effect', *, under_control: bool=False, exhaust: bool=False, target_game_area: 'GameArea|None'=None) -> bool:
        from game.operate.faces import Faces

        this = self.GetThis()
        if by_effect.world.is_game_over:
            return False
        this.card.MoveToTop(this.card.area, by_effect)

        if player == "CurrentPlayer":
            player = this.card.world.GetCurrentPlayer()
        elif player == "FirstPlayer":
            player = this.card.world.GetCurrentPlayer()
        if under_control:
            this.card.TakeControl(player)

        if not this.IsFaceUp():
            this.FlipTo(by_effect, face_up=True)
        from_area = this.card.area

        if exhaust:
            # See also "38028", "40171"
            def action(effect: 'Effect', message: 'Message.WhenCardEnterPlay'):
                Faces.ExhaustAll([message.trigger], effect)

            this.effect.RegisterTemp(
                AbilityFactory.WhenCardEnterPlay(
                    AbilityType.Temp0,
                    this,
                    action,
                ),
                unregister_after_exec=True,
                until_phase_end=True
            )

        message = Message.WhenCardPutIntoPlay(this, player, from_area, by_effect, target_game_area)
        if not this.OnPutIntoPlay(message):
            return False

        message = Message.AfterCardPutIntoPlay(this, message)
        self.OnAfterCardPutIntoPlay(message)
        return True

    ################################################################################
    #
    def OnWhenCardWouldReveal(self, message: 'Message.WhenCardWouldReveal') -> bool:
        message.Send()
        return True

    def OnPlayerRevealCard(self, message: 'Message.WhenPlayerRevealCard') -> bool:
        message.Send()
        return True

    def OnWhenCardRevealed(self, revealed_message: 'Message.WhenCardRevealed') -> None:
        from game.card.face.attribute.can_incite import CanIncite
        from game.card.face.attribute.can_surge import CanSurge
        this = self.GetThis()

        keyword_effects: List['Effect'] = []
        def add_resolved(message: 'Message.WhenCardRevealed', effect: 'Effect|None') -> None:
            if effect:
                message.reveal_message.AddResolved(effect)

        had_surge = CanSurge.IsType(this) and bool(this.surge)
        if CanIncite.IsType(this) and this.incite:
            keyword_effects += this.effect.RegisterTemp(
                Ability(
                    AbilityType.WhenRevealed,
                    Message.WhenCardRevealed,
                    [Condition2.ThisIsTrigger],
                    lambda effect, message:
                        add_resolved(message, effect.this.CastTo(CanIncite).ResolveIncite()),
                    is_local=True,
                ).SetName("Incite"),
                unregister_after_exec=True,
            )
        if had_surge:
            keyword_effects += this.effect.RegisterTemp(
                Ability(
                    AbilityType.WhenRevealed,
                    Message.WhenCardRevealed,
                    [Condition2.ThisIsTrigger],
                    lambda effect, message:
                        add_resolved(
                            message,
                            effect.this.CastTo(CanSurge).ResolveSurge(
                                message.GetToPlayer()
                            ),
                        ),
                    is_local=True,
                ).SetName("Surge"),
                unregister_after_exec=True,
            )
        if not revealed_message.reveal_message.cancel_when_revealed:
            revealed_message.Send()

            # Some When Revealed abilities grant Surge conditionally (for
            # example, Assault in alter-ego form and Hard to Keep Down when
            # the villain cannot heal). Printed Surge is scheduled above, but
            # a keyword gained while this message is resolving must be checked
            # afterwards so it is not missed.
            if CanSurge.IsType(this) and not had_surge and this.surge:
                add_resolved(
                    revealed_message,
                    this.ResolveSurge(revealed_message.GetToPlayer()),
                )

        # Canceled When Revealed effects never execute and therefore do not
        # reach their normal unregister-after-exec cleanup.
        for keyword_effect in keyword_effects:
            if not keyword_effect.is_unregister:
                keyword_effect.UnRegisterSelf()

    def OnAfterCardRevealedEnd(self, message: 'Message.AfterCardRevealedEnd') -> None:
        this = self.GetThis()
        reveal_message = message.reveal_message
        if len(reveal_message.resolved) > 0:
            if message.revealed_message:
                after_message = Message.AfterCardRevealed(this, message.revealed_message)
                after_message.Send()
        message.Send()

    @final
    def Reveal(self, player: 'Player|None|Literal["FirstPlayer"]', by_effect: 'Effect',
                *,
                is_by_flipping: bool=False,
                if_no_entered_play: Callable[[], Any]|None=None,
                if_entered_play: Callable[[], Any]|None=None
                ) -> 'Message.WhenPlayerRevealCard|Message.WhenCardRevealed|None':
        from game.effect.rule import GameRule
        from game.message import Message
        from game.card.face.attribute.can_surge import CanSurge
        from game.card.face.card_type import MainScheme
        from game.operate.faces import Faces
        from game.operate.effects import Effects

        this = self.GetThis()
        world = this.card.world

        if player == "FirstPlayer":
            player = world.GetFirstPlayer()
        elif not player:
            player = world.GetCurrentPlayer()

        from_area = this.card.area
        if (this.IsInDeck() or this.card.area.flags.is_discards or this.card.area.flags.is_removed) and not this.card.area.flags.is_dealt_encounter and this.card.area != world.main_schemes_deck:
            Faces.MoveAllTo([this], player.dealt_encounter_cards, GameRule(this))

        would_message = Message.WhenCardWouldReveal(this, player, by_effect, from_area, is_by_flipping)
        this.OnWhenCardWouldReveal(would_message)
        if would_message.is_be_instead:
            return None

        if not this.IsInPlay():
            if not this.card.area.flags.is_boost_area: # Fix "32029"
                this.Reset(False)
                if not MainScheme.IsType(this):
                    Faces.MoveAllTo([this], world.area_revealing, by_effect)
                    Message.AfterCardsMovedToRevealingArea_Text([this])

        from game.card.face.base import EncounterNonVillainCard
        if EncounterNonVillainCard.IsType(this) and \
            this.ResolveV17UniqueReveal(player):
            return None

        assert this.card.state.is_revealing == False

        this.card.state.is_revealing = True
        world.event_manager.BeginRevealResponseDeferral()
        try:
            reveal_message = Message.WhenPlayerRevealCard(this, would_message)
            if not this.OnPlayerRevealCard(reveal_message):
                return None
            if reveal_message.is_be_instead: # "52008"
                return None

            entered = False
            def set_enter_play():
                nonlocal entered
                entered = True

            check_effects = this.effect.RegisterTemp(
                AbilityFactory.WhenCardEnterPlay(
                    AbilityType.Temp0,
                    None,
                    lambda effect, message:
                        set_enter_play(),
                    conditions=[
                        lambda effect, message:
                            self == message.trigger
                    ],
                ),
                unregister_after_exec=False
            )

            if not reveal_message.cancel_all_effects:
                revealed_message = Message.WhenCardRevealed(this, reveal_message)
                this.OnWhenCardRevealed(revealed_message)
            else:
                revealed_message = None
                # TODO: by_cancel_all_effects_effect
                # When be cancelled by "01075", it should already be discarded by it
                # Faces.DiscardAll([this], GameRule(this))

#                       |   cancel all  | cancel when reveal (keep keywords such as "Incite")
# revealed_message      |   None        | None
# reveal_message        |   Yes         | Yes
#
            if not reveal_message.cancel_all_effects:
                end_message = Message.AfterCardRevealedEnd(this, reveal_message, revealed_message)
                this.OnAfterCardRevealedEnd(end_message)

            Effects.UnRegister(check_effects)

            if not entered:
                if if_no_entered_play:
                    if_no_entered_play()
            else:
                if if_entered_play:
                    if_entered_play()

            if revealed_message:
                return revealed_message
            else:
                return reveal_message
        finally:
            # Forced Responses and Responses triggered by entering play,
            # engaging, Incite/Surge, and reveal completion all open only after
            # this card has finished its complete reveal process.
            this.card.state.is_revealing = False
            world.event_manager.EndRevealResponseDeferral()

    ################################################################################
    #
    def OnWhenCardEnterPlay(self, message: 'Message.WhenCardEnterPlay') -> bool:
        this = self.GetThis()
        message.Send()
        if not this.IsInPlay():
            return False

        # this.card.components.OnWhenEnterPlay()
        return True

    def OnAfterCardEnterPlay(self, message: 'Message.AfterCardEnterPlay') -> None:
        message.Send()

    @final
    def ApplyAfterEnterPlay(self, from_area: 'Deck', into_area: 'Deck', by_effect: 'Effect', is_flip: bool):
        from game.message import Message
        this = self.GetThis()
        enter_play_message = Message.WhenCardEnterPlay(this, by_effect, is_flip=is_flip)
        if not this.OnWhenCardEnterPlay(enter_play_message):
            return

        # "32088b"
        # assert this.card.area == into_area, f"{this.card.area=} {into_area=}"
        after_message = Message.AfterCardEnterPlay(this, from_area, into_area, by_effect, enter_play_message)
        this.OnAfterCardEnterPlay(after_message)
        # if not this.IsInPlay():
        #     return

    ################################################################################
    #
    def OnDefeating(self, message: 'Message.WhenCardDefeating_Text') -> None:
        # this = self.GetThis()
        # this.card.components.OnDefeating()
        message.Send()

    def OnWouldDefeated(self, killer: 'CardFace|None', by_effect: 'Effect', being_message: 'Message.WhenSchemeBeingThwart|Message.WhenUnitBeingAttack|None') -> 'Message.WhenSchemeWouldBeDefeated|Message.WhenUnitWouldBeDefeated|None':
        return None

    def OnBeDefeated(self, would_defeated_message: 'Message.WhenSchemeWouldBeDefeated|Message.WhenUnitWouldBeDefeated', *, as_asset: bool, ignore_when_defeated: bool):
        Unused(as_asset)
        Unused(ignore_when_defeated)
        this = self.GetThis()
        for face in this.GetInventoryDeck().GetAll():
            face.OnBeDefeated(would_defeated_message, as_asset=True, ignore_when_defeated=False)

    @final
    def Defeated(self, killer: 'CardFace|None', by_effect: 'Effect', atk_message: 'Message.WhenSchemeBeingThwart|Message.WhenUnitBeingAttack|None'=None, *, ignore_when_defeated: bool=False) -> bool:
        would_defeat_message = self.CheckCanDefeated(killer, by_effect, atk_message)
        if would_defeat_message:
            self.WhenBeDefeated(would_defeat_message, ignore_when_defeated=ignore_when_defeated)
            return True
        return False

    @final
    def CheckCanDefeated(self, killer: 'CardFace|None', by_effect: 'Effect', atk_message: 'Message.WhenSchemeBeingThwart|Message.WhenUnitBeingAttack|None'=None) -> 'Message.WhenUnitWouldBeDefeated|Message.WhenSchemeWouldBeDefeated|None':
        would_defeat_message = self.OnWouldDefeated(killer, by_effect, atk_message)
        if would_defeat_message and not would_defeat_message.is_be_instead:
            return would_defeat_message
        return None

    @final
    def WhenBeDefeated(self, defeat_message: 'Message.WhenSchemeWouldBeDefeated|Message.WhenUnitWouldBeDefeated', *, ignore_when_defeated: bool=False) -> None:
        from game.message import Message
        this = self.GetThis()
        this.card.state.is_defeating = True
        defeating_message = Message.WhenCardDefeating_Text(this)
        self.OnDefeating(defeating_message)
        self.OnBeDefeated(defeat_message, as_asset=False, ignore_when_defeated=ignore_when_defeated)
        this.card.state.is_defeating = False

    ################################################################################
    #
    # @final
    # def Swap(self) -> None:
    #     from game.ability.rule import GameRule
    #     self.card.is_swapping = True
    #     for upgrade in self.card.components.inventory.GetDeck().Get():
    #         upgrade.OnUnattachUpgrade(self, True)
    #     self.BeforeFlip(GameRule(self))
    #     self.OnFlip(GameRule(self), None)
    #     self.card.is_swapping = False
    #     self.OnAfterFlip(GameRule(self))

    @final
    def OnBeforeSwapOld(self, by_effect: 'Effect', from_face: 'CardFace', no_detach: bool=False) -> None:
        this = self.GetThis()
        this.card.state.is_swapping_begin = True
        this.OnBeforeFlip(by_effect, no_detach=no_detach)
        this.card.state.is_swapping_begin = False

    @final
    def OnBeforeSwap(self, by_effect: 'Effect', to_face: 'CardFace', no_detach: bool=False) -> None:
        this = self.GetThis()
        this.card.state.is_swapping_begin = True
        # Fix "45144" "45145" "38011"
        this.OnBeforeFlip(by_effect, no_detach=no_detach)
        this.card.face = to_face
        this.card.face.card = this.card
        to_face.OnBeforeFlip(by_effect, no_detach=no_detach)
        this.card.state.is_swapping_begin = False

    @final
    def OnAfterSwap(self, by_effect: 'Effect', call_reveal: bool=False) -> None:
        this = self.GetThis()

        this.OnFlip(by_effect, None)

        this.card.state.is_swapping_end = True
        this.OnAfterFlip(by_effect, call_reveal=call_reveal)
        this.card.state.is_swapping_end = False
