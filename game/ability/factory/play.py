from . import *

class AbilityFactoryPlay:

    ################################################################################
    # Play
    @staticmethod
    def CanPlayThisSupportCard(*,
                               under_any_players_control: bool=False,
                               conditions: ConditionsType[Message.WhenPlayerInTurn]=[],
                               ) -> 'Ability':

        if under_any_players_control:
            selector = Select.From("Players")
        else:
            selector = Select.From("YourIdentity")

        return AbilityFactoryPlay.CanPlayThisSupportCardSelect(
            selector,
            conditions=conditions
        )

    @staticmethod
    def CanPlayThisSupportCardSelect(selector: 'Selector|None'=None,
                                    *,
                                    conditions: ConditionsType[Message.WhenPlayerInTurn]=[],
                                    ) -> 'Ability':
        """
        select = Select.YourIdentity
        """
        from game.selector import Select
        from game.card.face.card_type import Support
        from game.ability.factory import AbilityFactory
        from game.player import Player

        if selector == None:
            selector = Select.From("YourIdentity")

        def max_per_unit(effect: 'Effect', target: 'CardFace') -> bool:
            this = effect.this.CastTo(Support)
            if not Player.IsType(target.GetControlBy()):
                return False
            return this.max_per_unit > target.GetControlByPlayer().supports.HasThisType(this)

        selector.selector_filter.AddParameter(check_effect_fn=max_per_unit)

        def move_this_card(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
            this = effect.this.CastTo(Support)
            target = effect.targets[0]
            this.PutIntoPlay(target.GetControlByPlayer(), effect)

        return AbilityFactory.WhenInYourPlayTurn(
            AbilityType.PlayTurnOption,
            move_this_card,
            conditions=[
                lambda effect, message:
                    Condition.FieldHasNotThisUniqueType(effect.this, effect),
                *conditions
            ],
        ).SetPlay().SetTargetInternal(selector)

    # "Players" -> Play under any player's control
    @staticmethod
    def CanPlayThisUpgradeCard(target: 'CardFinder|Type[CardFace]|Literal["Players"]|Selector|None'=None,
                                # check_fn: Callable[['Effect', 'TC'], bool]|None=None,
                            #    check_fn: Callable[]|None=None
                            #    select: 'Select|Type['TC']|Literal["Players"]|None'=None,
                                conditions: ConditionsType[Message.WhenPlayerInTurn]=[],
                                replaced_operation: OperationType[Message.WhenPlayerInTurn]|None=None,
                                # when_attach_operation: Callable[['CardFace', 'Effect'], Any]|None=None,
                                ) -> 'Ability':
        from game.selector import Select
        from game.card.card_finder import CardFinder
        from game.ability.factory import AbilityFactory
        from game.card.face.card_type import Upgrade

        if target == None:
            selector = None
        elif isinstance(target, type):
            selector = Select.From(CardFinder(card_type=target))
        elif isinstance(target, CardFinder):
            selector = Select.From(target)
        elif isinstance(target, Selector):
            selector = target
        else:
            selector = Select.From(target)

        def attach_to_target(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
            from game.card.face.base import Asset2
            from game.operate.faces import Faces
            from game.operate.worlds import Worlds
            this = effect.this.CastTo(Asset2)

            if not replaced_operation:

                do_attached = False
                if effect.targets:
                    player = Worlds.GetFirstPlayer(effect)
                    target = player.AskChooseFace(effect.targets, effect)
                    if target:
                        this.AttachTo2(target, effect)
                        do_attached = True
                        # if when_attach_operation:
                        #     when_attach_operation(target, effect)
                if not do_attached:
                    Faces.DiscardAll([this], effect)

            else:
                replaced_operation(effect, message)

        # if isinstance(select, Selector):
        #     pass
        # elif select == None:
        #     select = Select(None, CardFinder(card_type=Identity)))
        # elif isinstance(select, str):
        #     select = Select(select)
        # else:
        #     select = Select(None, CardFinder(card_type=select))
        if selector == None:
            selector = Select.From("YourIdentity")

        def max_per_unit(effect: 'Effect', target: 'CardFace') -> bool:
            this = effect.this.CastTo(Upgrade)
            return this.max_per_unit > target.GetInventoryDeck().HasThisType(this)

        selector.selector_filter.AddParameter(check_effect_fn=max_per_unit)

        # For "45017", `CanBeAttachedTo`
        # assert select in [Select.YourIdentity, Select.OnFieldPlayers, Select.OnFieldAllies, Select.OnFieldSideSchemes, Select.OnFieldMinions, Select.OnFieldEnemies, Select.OnFieldFriendlyCharacters, Select.OnFieldSchemes, Select.OnFieldCharacters, Select.YourAllies, Select.MainSchemes]
        return AbilityFactory.WhenInYourPlayTurn(
            AbilityType.PlayTurnOption,
            attach_to_target,
            conditions=[
                lambda effect, message:
                    Condition.FieldHasNotThisUniqueType(effect.this, effect),
                *conditions
            ],
        ).SetPlay().SetTargetInternal(selector)

    @staticmethod
    def CanPlayThisAllyCard() -> 'Ability':
        from game.card.face.card_type import Ally
        from game.ability.factory import AbilityFactory
        def put_into_play(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
            from cards.pack.aoa.campaign import (
                HasActiveMission,
                MustPlayNextAllyToMission,
                PlayAllyToMission,
            )

            this = effect.this.CastTo(Ally)
            target = effect.targets[0]
            player = target.GetControlByPlayer()

            if HasActiveMission(effect):
                if MustPlayNextAllyToMission(player, effect):
                    PlayAllyToMission(this, player, effect)
                    return

                player.ChooseAbilities(
                    effect,
                    AbilityFactory.ForChoiceAbility(
                        "Play this ally under your control",
                        lambda targets:
                            this.PutIntoPlay(player, effect),
                    ),
                    AbilityFactory.ForChoiceAbility(
                        "Play this ally to the mission",
                        lambda targets:
                            PlayAllyToMission(this, player, effect),
                    ),
                )
                return

            this.PutIntoPlay(player, effect)
            # this.card.MoveToArea(target.GetControlByPlayer().allies, effect)

        def professor_x_cannot_enter_play(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> bool:
            from game.operate.store import Stores
            from game.operate.worlds import Worlds

            return not (
                Worlds.IsCampaignSelected(effect, "age_of_apocalypse") and
                Stores.HasKey("Age of Apocalypse Scenario", effect) and
                Stores.GetStr("Age of Apocalypse Scenario", effect) == "5" and
                effect.this.IsName("* Professor X")
            )

        return AbilityFactory.WhenInYourPlayTurn(
            AbilityType.PlayTurnOption,
            put_into_play,
            conditions=[
                lambda effect, message:
                    Condition.FieldHasNotThisUniqueType(effect.this, effect),
                professor_x_cannot_enter_play,
            ],
        ).SetPlay().SetTarget("YourIdentity")

    # Player side scheme
    @staticmethod
    def CanPlayThisSchemeCard(*, conditions: ConditionsType[Message.WhenPlayerInTurn]=[]
                                ) -> 'Ability':
        from game.card.face.card_type import PlayerSideScheme
        from game.ability.factory import AbilityFactory
        def put_into_play(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
            this = effect.this.CastTo(PlayerSideScheme)
            initiator = effect.GetInitiator()
            game_area = initiator.GetGameArea()
            this.PutIntoPlay(initiator, effect, target_game_area=game_area)

        # def check_limit(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> bool:
        #     limit_num = (effect.world.started_player_num+1) // 2
        #     faces = [x for x in effect.world.area_schemes_side.Get(True) if PlayerSideScheme.IsType(x)]
        #     if len(faces) < limit_num:
        #         return True
        #     else:
        #         return False

        return AbilityFactory.WhenInYourPlayTurn(
            AbilityType.PlayTurnOption,
            put_into_play,
            conditions=[
                lambda effect, message:
                    Condition.FieldHasNotThisUniqueType(effect.this, effect),
                # check_limit,
                *conditions
            ],
        ).SetPlay()

    @staticmethod
    def WhenPlayerWouldPlayCard(ability_type: 'AbilityType',
                                which_player: PlayerType,
                                which_card: CardType,
                                operation: OperationType[Message.WhenPlayerWouldPlayCard],
                                *,
                                label: 'Ability.LABEL|None'=None,
                                conditions: ConditionsType[Message.WhenPlayerWouldPlayCard]=[],
                                ) -> 'Ability':

        def check_which_player(effect: 'Effect', message: 'Message.WhenPlayerWouldPlayCard') -> bool:
            return Condition.CheckWhichPlayer(which_player, message.to_player, effect)

        def check_which_card(effect: 'Effect', message: 'Message.WhenPlayerWouldPlayCard') -> bool:
            return Condition.CheckWhichCard(which_card, message.play_face, effect)

        def check_label(effect: 'Effect', message: 'Message.WhenPlayerWouldPlayCard') -> bool:
            if not label:
                return True
            return message.play_effect.ability.IsLabel(label)

        return Ability(
            ability_type,
            Message.WhenPlayerWouldPlayCard,
            [
                check_which_player,
                check_which_card,
                check_label,
                *conditions
            ],
            operation,
            is_local=which_card == "This"
        )

    @staticmethod
    def WhenPlayerPlayCard(ability_type: 'AbilityType',
                           which_player: PlayerType,
                           played_card: 'CardFinder|None',
                           operation: OperationType[Message.WhenPlayerPlayCard],
                           *,
                           label: 'Ability.LABEL|None'=None,
                           targets: CardType=None,
                           using_res: "Resources.RBY|None"=None,
                           conditions: ConditionsType[Message.WhenPlayerPlayCard]=[],
                           ) -> 'Ability':

        def check_which_player(effect: 'Effect', message: 'Message.WhenPlayerPlayCard') -> bool:
            return Condition.CheckWhichPlayer(which_player, message.to_player, effect)

        def check_played_card(effect: 'Effect', message: 'Message.WhenPlayerPlayCard') -> bool:
            if played_card == None:
                return True
            return played_card.Check(message.played_face)

        def check_label(effect: 'Effect', message: 'Message.WhenPlayerPlayCard') -> bool:
            if not label:
                return True
            return message.played_effect.ability.IsLabel(label)

        def check_targets(effect: 'Effect', message: 'Message.WhenPlayerPlayCard') -> bool:
            if targets == None:
                return True
            return Condition.CheckWhichCard(targets, message.played_effect.targets, effect)

        def check_using_res(effect: 'Effect', message: 'Message.WhenPlayerPlayCard') -> bool:
            if using_res == None:
                return True
            return message.paid_resources.HasColor(using_res)

        return Ability(
            ability_type,
            Message.WhenPlayerPlayCard,
            [
                check_which_player,
                check_played_card,
                check_label,
                check_targets,
                check_using_res,
                *conditions
            ],
            operation,
            # local=played_card == "This"
        )

    @staticmethod
    def AfterPlayerPlayedCard(ability_type: 'AbilityType',
                              which_player: PlayerType,
                              which_card: CardType,
                              operation: OperationType[Message.AfterPlayerPlayedCard],
                              *,
                              from_hand: bool=False,
                              conditions: ConditionsType[Message.AfterPlayerPlayedCard]=[],
                              ) -> 'Ability':

        def invoke_operation(effect: 'Effect', message: 'Message.AfterPlayerPlayedCard') -> None:
            assert message.play_effect.ability.is_play
            operation(effect, message)

        def check_which_player(effect: 'Effect', message: 'Message.AfterPlayerPlayedCard') -> bool:
            return Condition.CheckWhichPlayer(which_player, message.to_player, effect)

        def check_which_card(effect: 'Effect', message: 'Message.AfterPlayerPlayedCard') -> bool:
            if isinstance(which_card, Message.WhenPlayerPlayCard):
                return message.play_message == which_card
            return Condition.CheckWhichCard(which_card, message.played_face, effect)

        def check_from_hand(effect: 'Effect', message: 'Message.AfterPlayerPlayedCard') -> bool:
            if from_hand:
                return message.is_like_from_hand
            return True

        return Ability(
            ability_type,
            Message.AfterPlayerPlayedCard,
            [
                check_which_card,
                check_which_player,
                check_from_hand,
                *conditions
            ],
            invoke_operation,
            is_local=which_card == "This"
        )

    @staticmethod
    def AfterYouPlayThisFromHand(ability_type: 'AbilityType',
                                operation: OperationType[Message.AfterPlayerPlayedCard],
                                *,
                                conditions: ConditionsType[Message.AfterPlayerPlayedCard]=[],
                                ) -> 'Ability':
        return AbilityFactoryPlay.AfterPlayerPlayedCard(
            ability_type,
            "You",
            "This",
            operation,
            from_hand=True,
            conditions=conditions
        )

    ################################################################################
    # Like in hand
    # Will also make the card can be visit
    @staticmethod
    def AttachedCardCanPlayLikeInHand(card_finder: 'CardFinder|None'=None,) -> List['Ability']:
        return AbilityFactoryPlay.YouMayPlayCardLikeInHand(
            AbilityType.NonKeyword,
            card_finder,
            from_where="ThisPlacedCard",
            during=None,
        )

    @staticmethod
    def YouMayPlayCardLikeInHand(ability_type: 'AbilityType',
                                which_card: CardType=None,
                                *,
                                from_where: Literal["YourDiscardPile", "ThisPlacedCard", "YourDeckTop"]|None=None,
                                during: Literal["YourTurn"]|None=None,
                                conditions: ConditionsType[Message.CheckIfFaceIsLikeInHand]=[],
                                ) -> List['Ability']:
        from game.ability.factory import AbilityFactory

        def check_which_card(effect: 'Effect', message: 'Message.CheckIfFaceIsLikeInHand') -> bool:
            return Condition.CheckWhichCard(which_card, message.which_face, effect)

        def check_from_where(effect: 'Effect', message: 'Message.CheckIfFaceIsLikeInHand') -> bool:
            if from_where == None:
                return True

            face = message.which_face
            if from_where == "ThisPlacedCard":
                return effect.this.GetPlacedCardArea() == face.card.area
            if from_where == "YourDiscardPile":
                return face.card.area.flags.is_discards
            if from_where == "YourDeckTop":
                return face.card.area.flags.is_player_deck and face.card.area.GetTop() == face
            return False

        def check_during(effect: 'Effect', message: 'Message.CheckIfFaceIsLikeInHand') -> bool:
            if during == None:
                return True
            if during == "YourTurn":
                return effect.GetInitiator() == effect.world.GetTurnPlayer()
            return False

        def set_like_in_hand(effect: 'Effect', message: 'Message.CheckIfFaceIsLikeInHand') -> None:
            message.SetIsLikeInHand(effect)

        abilty = Ability(
            ability_type,
            Message.CheckIfFaceIsLikeInHand,
            [
                check_which_card,
                check_from_where,
                check_during,
                *conditions
            ],
            set_like_in_hand,
            is_local=which_card == "This"
        )

        if which_card == "This":
            abilty.NoOutOfPlayLimit()

        abilties = [abilty]
        if during == "YourTurn":
            assert which_card == "This"
            def reset_is_like_in_hand_state(effect: 'Effect', message: 'Message.WhenPlayerTurnBegin'):
                effect.this.card.can_state.is_like_in_hand = None
            reset_ability = AbilityFactory.WhenPlayerTurnBegin(
                AbilityType.Rule,
                'AnyPlayer',
                reset_is_like_in_hand_state,
            )
            abilties.append(reset_ability)
        return abilties

    ################################################################################
    #
    @staticmethod
    def UnitIgnoreKeywordIcons(which_unit: CardType|Literal["You"],
                               guard: bool=False,
                               patrol: bool=False,
                               crisis: bool=False,
                               while_use_basic_thw: bool|None=None,
                               conditions: ConditionsType[Message.CheckIfEffectIsIgnoreKeyWord]=[],) -> 'Ability':
        from game.card.face.card_type import Event
        from game.card.face import Upgrade

        keywords: List[Literal['Guard', 'Patrol', 'Crisis']] = []
        if guard:
            keywords.append("Guard")
        if patrol:
            keywords.append("Patrol")
        if crisis:
            keywords.append("Crisis")

        def check_which_unit(effect: 'Effect', message: 'Message.CheckIfEffectIsIgnoreKeyWord') -> bool:
            by_effect = message.effect
            if Event.IsType(by_effect.this):
                # by_effect.ability.IsSubType('Attack') or by_effect.ability.IsSubType('Thwart'):
                by_face = message.effect.this.GetControlByOrOwner().GetRoleCharacter()
            elif Upgrade.IsType(by_effect.this):
                by_face = by_effect.this.GetBindFace()
            else:
                by_face = by_effect.this

            if which_unit == "You": # Fix "32030a" "32039"
                check_unit = "This"
            else:
                check_unit = which_unit
            return Condition.CheckWhichCard(check_unit, by_face, effect)

        return Ability(
            AbilityType.NonKeyword,
            Message.CheckIfEffectIsIgnoreKeyWord,
            [
                lambda effect, message:
                    message.keyword in keywords,
                check_which_unit,
                *conditions
            ],
            lambda effect, message:
                message.SetIgnore(),
            is_local=which_unit == "This"
        )
