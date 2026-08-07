from . import *

class AbilityFactoryDeck:

    ################################################################################
    # Deck
    @staticmethod
    def AfterDeckShuffle(ability_type: 'AbilityType',
                        deck: Callable[['Effect'], 'Deck']|Callable[['Effect'], List['Deck']],
                        operation: OperationType[Message.AfterDeckShuffle],
                        *,
                        conditions: ConditionsType[Message.AfterDeckShuffle]=[],
                        ) -> 'Ability':

        def check_deck(effect: 'Effect', message: 'Message.AfterDeckShuffle') -> bool:
            the_deck = deck(effect)
            if isinstance(the_deck, list):
                return message.deck in the_deck
            else:
                return the_deck == message.deck

        return Ability(
            ability_type,
            Message.AfterDeckShuffle,
            [
                check_deck,
                *conditions
            ],
            operation,
        )

    @staticmethod
    def AfterDeckRunOut(ability_type: 'AbilityType',
                        deck: Callable[['Effect'], 'Deck'],
                        operation: OperationType[Message.AfterDeckRunOut],
                        *,
                        conditions: ConditionsType[Message.AfterDeckRunOut]=[],
                        ) -> 'Ability':

        def check_deck(effect: 'Effect', message: 'Message.AfterDeckRunOut') -> bool:
            return deck(effect) == message.deck

        return Ability(
            ability_type,
            Message.AfterDeckRunOut,
            [
                check_deck,
                *conditions
            ],
            operation,
        )

    @staticmethod
    def AfterDeckReset(ability_type: 'AbilityType',
                        deck: Callable[['Effect'], 'Deck']|None,
                        operation: OperationType[Message.AfterDeckReset],
                        *,
                        conditions: ConditionsType[Message.AfterDeckReset]=[],
                        is_player_deck: bool|None=None,
                        ) -> 'Ability':

        def check_deck(effect: 'Effect', message: 'Message.AfterDeckReset') -> bool:
            if deck == None:
                return True
            return deck(effect) == message.deck

        def check_is_player_deck(effect: 'Effect', message: 'Message.AfterDeckReset') -> bool:
            if is_player_deck == None:
                return True
            return is_player_deck == message.deck.flags.is_player_deck

        return Ability(
            ability_type,
            Message.AfterDeckReset,
            [
                check_deck,
                check_is_player_deck,
                *conditions
            ],
            operation,
        )

    @staticmethod
    def PlayWithTopCardOfDeckFaceup(which_deck: Callable[['Effect'], List['Deck']],
                                    *,
                                    ex_operation: Callable[['CardFace', 'Effect'], None]|None=None,
                                    only_during_player_phase: bool=False,
                                    ) -> List['Ability']:
        from game.ability.factory import AbilityFactory

        def check_only_during_player_phase(effect: 'Effect', message: 'Message.AfterCardsMoved|Message.AfterDeckShuffle|Message.AfterUnitChangeForm|Message.WhenUnitWouldChangeForm') -> bool:
            if only_during_player_phase == False:
                return True
            assert ex_operation == None # HACK
            return effect.world.phase.IsPlayerPhase("AnyPlayer")

        def magik(effect: 'Effect', message: 'Message.AfterCardsMoved|Message.AfterDeckShuffle|Message.AfterUnitChangeForm|Message.WhenUnitWouldChangeForm|Message.WhenPhaseBegin') -> None:
            for deck in which_deck(effect):
                face = deck.GetTop()
                if face:
                    # A top-deck play permission can change when the deck,
                    # phase, or identity form changes. Do not retain a stale
                    # IsLikeInHand result from the previous state.
                    face.card.can_state.is_like_in_hand = None
                    face.FlipTo(effect, face_up=True, ui_look_at=True)

                    if ex_operation:
                        ex_operation(face, effect)

        abilities: List['Ability'] = []
        if only_during_player_phase:
            abilities.append(
                AbilityFactory.WhenPlayerPhaseBegin(
                    AbilityType.NonKeyword,
                    magik,
                )
            )

        return [
            *abilities,
            AbilityFactory.AfterCardsMoved(
                AbilityType.NonKeyword,
                None,
                magik,
                by_shuffle=False,
                conditions=[
                    check_only_during_player_phase
                ]
            ),
            AbilityFactory.AfterDeckShuffle(
                AbilityType.NonKeyword,
                which_deck,
                magik,
                conditions=[
                    check_only_during_player_phase
                ]
            ),
            AbilityFactory.AfterUnitChangeForm(
                AbilityType.NonKeyword,
                "This",
                magik,
                to_this_form=True,
                conditions=[
                    check_only_during_player_phase
                ]
            ),
            AbilityFactory.WhenUnitWouldChangeForm(
                AbilityType.NonKeyword,
                "This",
                magik,
                conditions=[
                    check_only_during_player_phase
                ]
            ),
        ]
