from . import *

class AbilityFactoryAsset:

    @staticmethod
    def GiveKeywordToAttached(
        card_finder: CardFinder|Literal["Character", "You"]|Type['TC']|None=None,
        *,
        get_new_value: Callable[['Effect', 'TC', List['CardFace']], int]|None=None, # condition, for each `[by_effect, attach]`
        expert_mode_only: Literal[True]|None=None,
        # name: str|None=None,
        # ignore flip
        health: Callable[['Effect'], int]|int|Literal["3*", "6*"]|None=None,
        considered_at_least_hp: int|None=None,
        # not ignore flip
        # multiple_player_icon: bool=False,
        trait: "CardFace.TRAITS|None"=None,
        attack: int|None=None,
        defense: int|None=None,
        thwart: int|None=None,
        scheme: int|None=None,
        retaliate: int|None=None,
        hand_size: int|None=None,
        stalwart: int|None=None,
        recover: int|None=None,
        guard: int|None=None,
        patrol: int|None=None,
        steady: int|None=None,
        treat_as_blank: bool|None=None,
        target_threat: int|None=None,
        control_additional_restricted: 'CardFinder|None'=None,
        attack_consequential_damage: int|None=None,
        thwart_consequential_damage: int|None=None,
        assault: int|None=None,
        have_res_icon: "Resources.RBYG|None"=None,
        apply: Callable[['Effect','CardFace', int], None]|None=None,
        #
        ex_change_on_event: EventType=OnEvent.NONE,
    ) -> List['Ability']:
        # from game.operate.worlds import Worlds

        abilities: List['Ability'] = []
        def only_ignore_flip() -> bool:
            return \
                trait == None and \
                attack == None and \
                defense == None and \
                thwart == None and \
                scheme == None and \
                retaliate == None and \
                hand_size == None and \
                stalwart == None and \
                recover == None and \
                guard == None and \
                patrol == None and \
                steady == None and \
                treat_as_blank == None and \
                target_threat == None and \
                control_additional_restricted == None and \
                attack_consequential_damage == None and \
                thwart_consequential_damage == None and \
                assault == None and \
                have_res_icon == None and \
                apply == None and \
                ( \
                    health != None or \
                    considered_at_least_hp != None \
                )
        # if multiple_player_icon:
        #     assert get_new_value == None
        #     get_new_value = lambda effect, face: Worlds.GetPlayerNumIcon(effect)
        from game.ability.factory.asset_helper import GiveKeywordToAttachWhenApplyThisInternal

        if not only_ignore_flip():
            abilities.append(
                GiveKeywordToAttachWhenApplyThisInternal(
                    card_finder,
                    ignore_flip=False,
                    get_new_value=get_new_value,
                    expert_mode_only=expert_mode_only,
                    trait=trait,
                    attack=attack,
                    defense=defense,
                    thwart=thwart,
                    scheme=scheme,
                    retaliate=retaliate,
                    hand_size=hand_size,
                    stalwart=stalwart,
                    recover=recover,
                    guard=guard,
                    patrol=patrol,
                    steady=steady,
                    treat_as_blank=treat_as_blank,
                    target_threat=target_threat,
                    control_additional_restricted=control_additional_restricted,
                    attack_consequential_damage=attack_consequential_damage,
                    thwart_consequential_damage=thwart_consequential_damage,
                    assault=assault,
                    have_res_icon=have_res_icon,
                    apply=apply,
                    ex_change_on_event=ex_change_on_event,
                )
            )
        if health != None or considered_at_least_hp != None:
            abilities.append(
                GiveKeywordToAttachWhenApplyThisInternal(
                    card_finder,
                    get_new_value=get_new_value,
                    expert_mode_only=expert_mode_only,
                    health=health,
                    considered_at_least_hp=considered_at_least_hp,
                    ignore_flip=True,
                    ex_change_on_event=ex_change_on_event,
                )
            )
        return abilities

    ################################################################################
    # Attach to
    @staticmethod
    def WhenCardWouldAttachTo(ability_type: 'AbilityType',
                            which_card: CardType,
                            to_where: CardType,
                            operation: OperationType[Message.WhenCardWouldAttachTo],
                            *,
                            conditions: ConditionsType[Message.WhenCardWouldAttachTo]=[],
                            ) -> 'Ability':

        def check_which_card(effect: 'Effect', message: 'Message.WhenCardWouldAttachTo') -> bool:
            return Condition.CheckWhichCard(which_card, message.upgrade, effect)

        def check_to_where(effect: 'Effect', message: 'Message.WhenCardWouldAttachTo') -> bool:
            return Condition.CheckWhichCard(to_where, message.to_face, effect)

        return Ability(
            ability_type,
            Message.WhenCardWouldAttachTo,
            [
                check_which_card,
                check_to_where,
                *conditions
            ],
            operation
        )

    @staticmethod
    def AttachToFaceWhenPutIntoPlayInternal(selector: 'Selector',
                                            *,
                                            conditions: ConditionsType[Message.WhenCardPutIntoPlay]=[],
                                            otherwise_selector: 'Selector|None'=None,
                                            if_cannot_operation: Callable[['Effect', 'Player'], None]|None=None,
                                            when_attach_operation: Callable[['CardFace', 'Effect'], Any]|None=None,
                                            ) -> 'Ability':
        from game.operate.filter import Filter

        def attach_to_card(effect: 'Effect', message: 'Message.WhenCardPutIntoPlay') -> None:
            from game.card.face.attribute.can_attach import CanAttach
            this = effect.this.CastTo(CanAttach)

            face = None
            targets = selector.GetAllLegalTargets(effect)
            if targets:
                face = Filter.One(targets, effect)
            elif otherwise_selector:
                targets = otherwise_selector.GetAllLegalTargets(effect)
                face = Filter.One(targets, effect)

            if face:
                this.AttachTo2(face, effect)
                if when_attach_operation:
                    when_attach_operation(face, effect)
            else:
                if if_cannot_operation:
                    player = message.GetToPlayer()
                    if_cannot_operation(effect, player)

            # RR 1.8 "Attach To": an attachment that cannot attach as it
            # enters play does not enter play.  The caller restores its prior
            # game area (or leaves an explicit fallback operation intact).
            if not this.card.state.is_attached:
                message.put_into_play_failed = True

        return Ability(
            AbilityType.NonKeyword,
            Message.WhenCardPutIntoPlay,
            [
                # Hasn't attached
                lambda effect, message:
                    effect.this == message.trigger,
                *conditions,
            ],
            attach_to_card,
            is_local=True
        ).NoOutOfPlayLimit().SetFuncName("AttachToWhenEnterPlay")

    @staticmethod
    def WhenThisBoostAttachTo(which_card: 'CardFinder'|Literal["ActivatingEnemy", "Minion", "Villain", "YouIdentity"],
                            *,
                            otherwise_attach_to: CardFinder|Type['TC']|None=None,
                            ex_operate: Callable[['CardFace', 'Effect'], Any]|None=None) -> 'Ability':
        from game.operate.worlds import Worlds
        from game.operate.filter import Filter
        from game.ability.factory import AbilityFactory
        from game.card.face.attribute.can_attach import CanAttach

        def adamantium_claws_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
            this = effect.this.CastTo(CanAttach)

            if which_card == "ActivatingEnemy":
                face = message.activating_enemy
            elif which_card == "Minion":
                face = Filter.One(Worlds.GetOnFieldMinions(effect), effect)
            elif which_card == "Villain":
                face = Worlds.FindVillain(effect)
            elif which_card == "YouIdentity":
                face = message.GetToPlayer().GetIdentity()
            else:
                faces = Worlds.FindCardsOnField(
                    effect,
                    which_card
                )
                face = Filter.One(faces, effect)

            if not face and otherwise_attach_to:
                if isinstance(otherwise_attach_to, CardFinder):
                    otherwise_selector = otherwise_attach_to
                else:
                    otherwise_selector = CardFinder(card_type=otherwise_attach_to)

                faces = Worlds.FindCardsOnField(
                    effect,
                    otherwise_selector
                )
                face = Filter.One(faces, effect)

            if face:
                this.AttachTo2(face, effect)
                if ex_operate:
                    ex_operate(face, effect)

        return AbilityFactory.WhenCardBecomeBoost(
            "This",
            adamantium_claws_boost
        )
