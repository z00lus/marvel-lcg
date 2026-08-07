from core import *
from game.card.face import *
from game.effect import *
from game.ability.factory import *
from game.selector import *
from game.player import *

HACK_HERO_ID = '3100'

class PlayerSetup:

    def __init__(self, player: 'Player') -> None:
        self.player = player

    def ValidateV17IdentitySelection(self, identity: 'CardFace') -> None:
        from game.card.face.card_type import Identity

        for player in self.player.world.const_players:
            for other_identity in player.area_hero.GetAll():
                if other_identity.card == identity.card:
                    continue
                if Identity.IsType(other_identity) and identity.MatchesV17Unique(other_identity):
                    raise ValueError(
                        f"Matching identities cannot be selected together: "
                        f"{identity.name} and {other_identity.name}"
                    )

    def ValidateV17DeckUniqueness(self, identity: 'CardFace', deck_faces: Sequence['CardFace']) -> None:
        unique_faces = [identity] + [face for face in deck_faces if face.IsUnique()]
        for index, face in enumerate(unique_faces):
            for other_face in unique_faces[index + 1:]:
                if face.MatchesV17Unique(other_face):
                    raise ValueError(
                        f"A player deck cannot contain matching unique cards: "
                        f"{face.name} and {other_face.name}"
                    )

    def SetupPlayerAbility(self, hero: 'CardFace'):
        from game.message import Message
        player = self.player

        def register_change_form():
            from game.ability import AbilityType
            from game.card.face.card_type import AlterEgo
            from game.card.face.card_type import Hero

            def add_change_form_effect(identity: 'AlterEgo|Hero', identities: List['AlterEgo|Hero']):

                def check_is_same_card(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> bool:
                    this = effect.this
                    if len(this.card.back_faces) == 1:
                        return True
                    # if this.paper.card_id in ["29001a", "29001b", "29002a", "29002b", "29003a", "29003b"]:
                    return face.paper.card_id[:-1] == this.card.face.paper.card_id[:-1]

                def invoke_change_form(to_face: 'AlterEgo|Hero', effect: 'Effect'):
                    initiator = effect.GetInitiator()
                    initiator.has_change_form = True
                    initiator.GetIdentity().ChangeToFace(to_face, effect)

                faces = identities[:]
                faces.remove(identity)

                if not identity.paper.card_id.startswith(HACK_HERO_ID) and len(identities) > 2:
                    faces = [x for x in faces if x.paper.card_id[:-1] == identity.paper.card_id[:-1]]

                for face in faces:
                    def register_change_to(face: 'AlterEgo|Hero', name: str):
                        identity.effect.Registers(
                            AbilityFactory.WhenInYourPlayTurn(
                                AbilityType.PlayTurnOption,
                                lambda effect, message:
                                    invoke_change_form(face, effect),
                                conditions=[
                                    lambda effect, message:
                                        not effect.GetInitiator().has_change_form and \
                                        identity.card.face != face and \
                                        identity.IsInPlay(is_same_face=True),
                                    check_is_same_card
                                ],
                            ).SetFuncName("Change Form").SetName(name).NoOutOfPlayLimit()
                        )

                    name = ""
                    if len(faces) > 1:
                        if face.name in [x.name for x in identities if x != face]:
                            name = face.traits_str
                            name = "Change To " + name.strip()
                        else:
                            name = "Change To " + face.name
                    register_change_to(face, name)

            identities: Set['AlterEgo|Hero'] = set([])
            for face in player.area_hero.GetAll() + [hero.card.face]:
                for identity in [face] + face.card.back_faces:
                    if isinstance(identity, AlterEgo|Hero):
                        identities.add(identity)
            for identity in sorted(identities):
                add_change_form_effect(identity, list(identities))

        def register_ask_effect():
            if player.world.GetPlayerNum() > 1:
                # In turn
                def invoke_ask(effect: 'Effect', message: 'Message.WhenPlayerInTurn'):
                    # v1.5
                    # Ask another player to trigger an “Action” ability on
                    # a card in play they control or on an event card they
                    # might have in hand. The other player then decides
                    # whether or not to trigger the ability. (Another player
                    # may offer to use an action during the active player’s
                    # turn, as well.)
                    # v1.6
                    # Ask another player to trigger any “Action” ability
                    # that player could trigger on their own turn. The other
                    # player then decides whether or not to trigger the
                    # ability. (Another player may offer to use an action
                    # during the active player’s turn, as well.)
                    def get_player_can_asked_effects(player: 'Player') -> List['Effect']:
                        return [
                            x
                            for x in 
                            effect.world.event_manager.FindEffectsList("Optional", Message.WhenPlayerInTurn, TimingPriority.Normal)
                            if
                            x.is_action
                        ]

                    with effect.targets[0].GetControlByPlayer() as player:
                        turn_message = Message.WhenPlayerLikeInTurn(player, effect)
                        turn_message.Send()
                        player.ChooseEffects(get_player_can_asked_effects(player), turn_message)

                hero.effect.Registers(
                    AbilityFactory.WhenInYourPlayTurn(
                        AbilityType.Ask,
                        lambda effect, message:
                            invoke_ask(effect, message)
                    ).SetFuncName("Ask")
                    .SetTarget("OtherPlayers")
                    .NoOutOfPlayLimit()
                )

                # Defense
                def get_player_can_def_effects(player: 'Player') -> List['Effect']:
                    effects: List[Effect] = []
                    for face in player.GetControlCharacters():
                        for face_effect in face.effects:
                            if face_effect.ability.IsFunction("DEF") and face.CanExhaust():
                                effects.append(face_effect)
                            elif face_effect.ability.IsLabel('defense'):
                                effects.append(face_effect)
                    return effects

                def invoke_defense(effect: 'Effect', message: 'Message.WhenUnitBeingAttack'):
                    with effect.targets[0].GetControlByPlayer() as player:
                        bing_atk_message = Message.WhenUnitLikeBeingAttack(player.GetIdentity(), message.would_atk_message, message)
                        bing_atk_message.Send()
                        player.ChooseEffects(get_player_can_def_effects(player), bing_atk_message)

                def on_field_other_players(effect: 'Effect') -> Sequence['AlterEgo|Hero']:
                    from game.card.face.card_type import AlterEgo
                    from game.card.face.card_type import Hero

                    units = Select.From("OtherPlayers").GetAllLegalTargets(effect)
                    return [x for x in units if get_player_can_def_effects(x.GetControlByPlayer()) != [] and isinstance(x, AlterEgo|Hero)]

                hero.effect.Registers(
                    Ability(
                        AbilityType.Ask,
                        Message.WhenUnitBeingAttack,
                        [
                            lambda effect, message:
                                message.defender == None and \
                                # not Enemy.IsType(message.trigger) and \
                                # effect.initiator == message.trigger.GetOwner(),
                                effect.initiator == message.trigger.card.GetController(),
                        ],
                        invoke_defense
                        # If the attacked player does not defend, any other player may defend against the attack by exhausting their hero or an ally they control
                    ).SetFuncName("Ask")
                    .SetTarget(on_field_other_players)
                    .NoOutOfPlayLimit()
                )

                # Resoruce
                # def invoke_res(effect: 'Effect', message: 'Send.WhenPlayerPayingResources'):
                #     player = effect.targets[0].GetPlayer()
                #     paying_message = Send.WhenPlayerLikePayingResources(player, message.for_effect)
                #     player.ChooseEffects(player.GetPayEffects(), paying_message)

                # hero.RegisterEffect(
                #     Ability(
                #         AbilityType.Ask,
                #         Send.WhenPlayerPayingResources,
                #         lambda effect, message:
                #             effect.GetInitiator() == message.to_player,
                #         do_res
                #     ).SetSubType('Ask')
                #     .SetTarget2(Select.OnFieldOtherPlayers).SetActiveOutOfPlay()
                # )

        register_change_form()
        register_ask_effect()

    def SelectIdentity(self, name: str, hero_names: Sequence[str], hero_deck: Sequence[str], obligations: Sequence[str], nemesis_set: Sequence[str], player_deck: Sequence[str]) -> None:
        from game.effect.rule import GameRule
        from game.message import Message
        from game.card.factory import CardFactory

        player = self.player

        player.hero_name = name

        def move_b_to_front(s: str):
            parts = s.split(',')
            b_part = [part for part in parts if part.endswith('b')]
            other_parts = [part for part in parts if not part.endswith('b')]
            result = b_part + other_parts
            return ','.join(result)
        if hero_names[0].startswith(HACK_HERO_ID):
            hero_names = ["31002a,31002b"]
        else:
            hero_names = [move_b_to_front(s) for s in hero_names]
        CardFactory.GenerateCards(hero_names, player.set_aside_deck, player.world)

        hero_card = player.set_aside_deck.GetAll()[0]
        self.ValidateV17IdentitySelection(hero_card)
        rule = GameRule(hero_card)
        hero_card.PutIntoPlay(player, rule)

        # hero_card.Reset(False)
        # hero_card.ResetHealth(GameRule(hero_card))
        # We do this by effect

        if player.world.is_game_over:
            return

        # CardFactory.GenerateCards(set_aside, player.set_aside_deck, player.world)
        select_message = Message.WhenPlayerSelectHero(player, player.GetIdentity())
        select_message.Send()

        # After set aside is create for `HACK_HERO_ID`
        if hero_card.card.back_faces:
            # hero_card.ChangeToForm(AlterEgo, GameRule(hero_card))
            self.SetupPlayerAbility(hero_card)

        # ~~3. Select First Player~~
        # We don't need this

        # 4. Set Aside Obligation
        player.set_aside_obligations = []
        player.set_aside_obligations += CardFactory.GenerateCards(obligations, player.set_aside_nemesis_sets, player.world)

        # 5. Set Aside Nemesis Sets
        CardFactory.GenerateCards(nemesis_set, player.set_aside_nemesis_sets, player.world)

        # 6. Shuffle Player Decks
        if player.world.rule.create_player_deck_first:
            player_hero_deck = list(player_deck) + list(hero_deck)
        else:
            player_hero_deck = list(hero_deck) + list(player_deck)
        generated_player_cards = CardFactory.GenerateCards(player_hero_deck, player.player_deck, player.world)
        if not getattr(player.world.rule, "mode_campaign", False):
            self.ValidateV17DeckUniqueness(
                player.GetIdentity(),
                [card.face for card in generated_player_cards],
            )

        player.stat.ResetPlayedRevealedCards()
        player.flag.Reset()
        player.res_pool.Reset()

        Message.WhenDeckCreated_Text(player.player_deck)
        # rule = GameRule(player.GetIdentity())
        player.player_deck.Shuffle(rule)

        if player.world.is_game_over:
            return

        selected_message = Message.AfterPlayerSelectHeroEnd(player, player.GetIdentity())
        selected_message.Send()
