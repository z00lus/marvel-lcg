from . import *

class HasHealth(HasAttribute, CanAttacked):

    @override
    def __init__(self, paper: 'Paper') -> None:
        self.printed_health = -1
        self.printed_health_numeral = -1
        self.starting_health = -1

        # 16-mc16_galaxys_most_wanted_rules_website-compressed.pdf
        # A character with infinite hit points cannot be defeated by
        # taking damage. However, damage may still be dealt to
        # that character through attacks and card abilities.

        # Some characters may have an infinite number of hit points.
        # A character with infinite hit points cannot be defeated by
        # taking damage, as the amount of damage that character
        # takes will never cause its remaining hit points to reach zero.
        # However, damage may still be dealt to a character with
        # infinite hit points through attacks and card abilities.
        self.is_infinite_health: bool = False

        self.considered_at_least_hp_dict: Dict['Effect', int] = {}

        self.base_health = 0
        # self.health_max = 0

        super().__init__(paper)

        def parse(value: str):
            if value == "INF":
                self.is_infinite_health = True
                self.printed_health = 0
                self.printed_health_numeral = 0
            else:
                self.printed_health = self.FormatPlayerNumValue(value)
                digit = ''.join(ch for ch in value if ch.isdigit())
                self.printed_health_numeral = int(digit)
            self.starting_health = self.printed_health
        self.RegisterAttribute("HP", parse)
        self.RegisterInfoDict('health')
        self.RegisterInfoDict('is_infinite_health')

    @override
    def CheckPrintedValue(self):
        if not self.is_infinite_health:
            assert self.printed_health >= 0, f"{self.paper.card_id=}"
        return super().CheckPrintedValue()

    @final
    @property
    def health(self) -> int:
        def get_health():
            if self.is_infinite_health:
                return 1 # if we set it 0, it cannot be attacked
            else:
                return self.components.health.GetHealth()
        health = get_health()
        considered_at_least_hp = self.considered_at_least_hp
        if considered_at_least_hp and \
            health < considered_at_least_hp:
            return considered_at_least_hp
        else:
            return health

    @final
    @property
    def considered_at_least_hp(self) -> int:
        health = 0
        for effect in self.considered_at_least_hp_dict:
            if health < self.considered_at_least_hp_dict[effect]:
                health = self.considered_at_least_hp_dict[effect]
        return health

    @final
    @property
    def max_health(self) -> int:
        if self.is_infinite_health:
            return 0
        else:
            return self.components.health.GetMaxHealth()

    @final
    @property
    def sustained(self) -> int:
        if self.is_infinite_health:
            return 0
        else:
            return self.max_health - self.health

    @final
    @property
    def is_full_heath(self) -> bool:
        if self.is_infinite_health:
            return True
        return self.sustained == 0

class CanHealth(HasHealth):

    @override
    def OnFlip(self, by_effect: 'Effect', origin_face: 'CardFace|None'):
        from game.effect.rule import ResetKeyword
        from game.card.face.base import Unit2
        self.base_health = self.printed_health
        self.considered_at_least_hp_dict = {}
        # self.health_max = self.base_health
        if origin_face and not Unit2.IsType(origin_face) or \
            origin_face and origin_face.is_infinite_health:
            self.ResetHealth(ResetKeyword(self))
        return super().OnFlip(by_effect, origin_face)

    @override
    def OnReset(self, message: 'Message.WhenCardReset_Text') -> None:
        self.components.health.SetHealth(0)
        self.components.health.SetMaxHealth(0)
        return super().OnReset(message)

    ################################################################################
    #
    @final
    def ResetHealth(self, by_effect: 'Effect', num: int|Literal["Max", "Printed", "10*"]="Max"):
        from game.card.face.base import Unit2
        from game.operate.worlds import Worlds

        self.base_health = self.printed_health
        self.components.health.SetMaxHealth(self.base_health)
        self.considered_at_least_hp_dict = {}

        if not isinstance(num, int):
            assert self.card.face == self

        # self.health_max = self.base_health
        if num == "Printed":
            health_max = self.printed_health
        elif num == "Max":
            health_max = self.max_health
        else:
            health_max = Worlds.ConvertPerPlayerIconToInt(num, by_effect)
        self.components.health.SetHealth(health_max)

        assert Unit2.IsType(self)
        reset_message = Message.AfterUnitHitPointReset(self, by_effect)
        reset_message.Send()

    @final
    def MoveDamage(self, damage: int, target: 'Unit2', by_effect: 'Effect'):
        # Q: Does moving damage discard tough status cards from
        # the target enemy?
        # A: Yes. If damage is moved to a character, the moved
        # damage is considered to be dealt to that character
        lost_heath = self.GetLostHealth()
        if lost_heath < damage:
            damage = lost_heath
        if damage != 0:
            self.HealHealth(damage, by_effect)
            if by_effect.ability.IsLabel('attack'):
                # Fix "01049" interaction with retaliate
                self.DealDamage([target], damage, by_effect)
            else:
                target.TakeDamage(self, damage, by_effect)

    @final
    def HealHealth(self, value: int|Literal["All", "Printed"], by_effect: 'Effect') -> 'Message.AfterUnitHealHealth|None':
        if not self.IsInPlay():
            return None

        if value == "All":
            value = self.sustained
        elif value == "Printed":
            value = self.printed_health - self.health

        message = self.GainOnlyHealth(value, by_effect)

        if isinstance(message, Message.AfterUnitHealHealth):
            return message
        else:
            return None

    @final
    def TakeIndirectDamage(self, source: 'CardFace', damage: int, by_effect: 'Effect', *, from_atk_message: 'Message.WhenUnitWouldAttack|None'=None, as_group: bool=False, operation: Callable[['Message.AfterUnitTookDamage'], None]|None=None):
        from game.operate.worlds import Worlds

        player = self.GetControlByPlayer()
        if as_group:
            units = Worlds.GetOnFieldFriendlyCharacters(by_effect)
        else:
            units = [player.GetIdentity()] + player.GetControlAllies()
        return player.AssignDamage(units, source, damage, by_effect, operation=operation, from_atk_message=from_atk_message)

    @override
    def TakeDamage(self, source: 'CardFace', property: 'int|DamageProperty', by_effect: 'Effect',
                    would_attack_unit_message: 'Message.WhenUnitWouldAttackUnit|None'=None,
                    *,
                    from_atk_message: 'Message.WhenUnitWouldAttack|None'=None, # Fix for indirect damage, "43036"
                    operation: Callable[['Message.AfterUnitTookDamage'], None]|None=None,
                    ) -> 'Message.AfterUnitDefeatedUnit|Message.AfterUnitTookDamage|None':
        messages = self.TakeDamageWithOverkillTarget(source, property, by_effect, would_attack_unit_message, from_atk_message=from_atk_message, operation=operation)
        if messages:
            return messages[0]
        return None

    @override
    # [0]: current
    # [1]: overkill target
    def TakeDamageWithOverkillTarget(self, source: 'CardFace', property: 'int|DamageProperty',
                                    by_effect: 'Effect',
                                    would_attack_unit_message: 'Message.WhenUnitWouldAttackUnit|None'=None,
                                    overkill_target: 'Unit2|None'=None,
                                    *,
                                    from_atk_message: 'Message.WhenUnitWouldAttack|None'=None, # Fix for indirect damage, "43036"
                                    operation: Callable[['Message.AfterUnitTookDamage'], None]|None=None
                                    ) -> List['Message.AfterUnitDefeatedUnit|Message.AfterUnitTookDamage']:
        return_messages: List['Message.AfterUnitDefeatedUnit|Message.AfterUnitTookDamage'] = []
        lost_message_helper = self.TakeDamageNoDeath(source, property, by_effect, would_attack_unit_message, from_atk_message=from_atk_message, operation=operation)
        if lost_message_helper != None:
            would_take_damage_message = lost_message_helper.would_take_damage_message
            lost_message = lost_message_helper.lost_message
            total_took_damage = lost_message.value if lost_message else 0
            excess_damage = lost_message_helper.excess_damage

            primary_defeated = False
            if lost_message and self.health <= 0:
                primary_defeated = self.Death(
                    source,
                    by_effect,
                    would_attack_unit_message,
                )
                if primary_defeated and would_attack_unit_message:
                    would_attack_unit_message.would_atk_message.has_defeated_target = True

            overkill_messages: List['Message.AfterUnitDefeatedUnit|Message.AfterUnitTookDamage'] = []
            damaged_overkill_target = None

            # Rules Reference 1.8: excess damage is not dealt until the ally or
            # minion has actually been defeated by this attack. Tough, damage
            # prevention/caps, and defeat replacements therefore stop here.
            if primary_defeated and \
                overkill_target and \
                overkill_target.IsInPlay() and \
                excess_damage > 0:
                overkill_helper = overkill_target.TakeDamageNoDeath(
                    source,
                    DamageProperty(
                        damage=excess_damage,
                        is_from_overkill=True,
                    ),
                    by_effect,
                    would_attack_unit_message,
                    from_atk_message=from_atk_message,
                )
                if overkill_helper != None:
                    overkill_lost_message = overkill_helper.lost_message
                    overkill_took_damage = overkill_lost_message.value if overkill_lost_message else 0
                    overkill_excess_damage = overkill_helper.excess_damage
                    overkill_defeated = False

                    if overkill_lost_message and overkill_target.health <= 0:
                        overkill_defeated = overkill_target.Death(
                            source,
                            by_effect,
                            would_attack_unit_message,
                        )
                        if overkill_defeated and would_attack_unit_message:
                            would_attack_unit_message.would_atk_message.has_defeated_target = True

                    if overkill_defeated:
                        overkill_message = Message.AfterUnitDefeatedUnit(
                            source,
                            overkill_target,
                            overkill_took_damage,
                            overkill_excess_damage,
                            None,
                            by_effect,
                            overkill_helper.would_take_damage_message,
                        )
                    elif overkill_lost_message:
                        overkill_message = Message.AfterUnitTookDamage(
                            overkill_target,
                            source,
                            overkill_took_damage,
                            by_effect,
                            overkill_helper.would_take_damage_message,
                            excess_damage=0,
                        )
                    else:
                        overkill_message = None

                    if overkill_message:
                        overkill_message.Send()
                        if isinstance(overkill_message, Message.AfterUnitTookDamage) and operation:
                            operation(overkill_message)
                        overkill_messages.append(overkill_message)
                        if overkill_message.took_damage > 0:
                            damaged_overkill_target = overkill_target

            if primary_defeated:
                # Fix defeating "27073" while "27081" is in play.
                if self.IsInPlay():
                    took_damage_message = Message.AfterUnitTookDamage(
                        self,
                        source,
                        total_took_damage - excess_damage,
                        by_effect,
                        would_take_damage_message,
                        excess_damage=excess_damage,
                    )
                    took_damage_message.Send()
                    if operation:
                        operation(took_damage_message)

                primary_message = Message.AfterUnitDefeatedUnit(
                    source,
                    self,
                    total_took_damage,
                    excess_damage,
                    damaged_overkill_target,
                    by_effect,
                    would_take_damage_message,
                )
            elif lost_message:
                damage = total_took_damage
                if overkill_target:
                    damage -= excess_damage
                primary_message = Message.AfterUnitTookDamage(
                    self,
                    source,
                    damage,
                    by_effect,
                    would_take_damage_message,
                    excess_damage=0,
                )
            else:
                primary_message = None

            if primary_message:
                primary_message.Send()
                if isinstance(primary_message, Message.AfterUnitTookDamage) and operation:
                    operation(primary_message)
                return_messages.append(primary_message)
            return_messages += overkill_messages

        if lost_message_helper and lost_message_helper.would_take_damage_message.would_deal_damage_message.damage > 0:
            after_damage_message = Message.AfterFaceDealDamage(
                lost_message_helper.would_take_damage_message.would_deal_damage_message,
                return_messages,
                by_effect)
            after_damage_message.Send()

        return return_messages

    @final
    def TakeDamageNoDeath(self, source: 'CardFace', property: 'int|DamageProperty', by_effect: 'Effect',
                    would_attack_unit_message: 'Message.WhenUnitWouldAttackUnit|None'=None,
                    *,
                    from_atk_message: 'Message.WhenUnitWouldAttack|None'=None, # Fix for indirect damage, "43036"
                    operation: Callable[['Message.AfterUnitTookDamage'], None]|None=None,
                    ) -> 'Message.AfterUnitLossHealthHelper|None':
        from game.card.face.base import Unit2
        # When player use event card, this == event card, but source == hero
        assert Unit2.IsType(self)
        this = self

        if this.IsDefeated():
            return None

        if isinstance(property, int):
            property = DamageProperty(property)

        if from_atk_message == None and would_attack_unit_message != None:
            from_atk_message = would_attack_unit_message.would_atk_message

        would_deal_damage_message = Message.WhenFaceWouldDealDamage(source, this, property, by_effect, would_attack_unit_message, from_atk_message)
        would_deal_damage_message.Send()
        assert property.damage == would_deal_damage_message.damage

        if would_deal_damage_message.is_be_instead:
            return None

        if property.damage <= 0:
            Message.WhenDamageIsZero_Text(this, source, True)
            return None

        # would_atk_message = being_atk_message.would_atk_message if being_atk_message else None

        # if not isinstance(being_atk_message, Send.WhenUnitBeingAttack):
        #     being_atk_message = None

        would_take_damage_message = Message.WhenUnitWouldTakeDamage(this, source, property, by_effect, would_deal_damage_message)
        would_take_damage_message.Send()
        if would_take_damage_message.is_be_instead:
            return None
        if would_attack_unit_message and not source.IsInPlay():
            return None
        value = would_take_damage_message.will_take_damage

        if value == 0 or would_take_damage_message.IsBePrevent():
            # Overkill damage is dealt simultaneously with the attack’s standard damage, and Nightcrawler can only prevent damage to one character.
            # if would_take_damage_message.be_prevent:
            #     excess_damage = 0
            # else:
            excess_damage = would_take_damage_message.overkill_damage
            return Message.AfterUnitLossHealthHelper(
                None, would_take_damage_message, excess_damage
            )

        if not would_take_damage_message.IsBePrevent():
            excess_damage = 0

            assert this.IsInPlay()

            max_sustained = would_take_damage_message.cannot_have_more_than_sustained

            damage_message = this.UpdateHealth(-1 * value, by_effect, max_sustained=max_sustained)
            if damage_message:
                if this.health < 0:
                    deal_message = Message.WhenCalcDealExcessDamage(
                        source,
                        this,
                        -1 * this.health,
                        by_effect,
                        would_attack_unit_message)
                    deal_message.Send()
                    excess_damage = deal_message.excess_damage

            if isinstance(damage_message, Message.AfterUnitLossHealth):
                # damage_message.excess_damage = excess_damage
                # damage_message.would_take_damage_message = would_take_damage_message
                return Message.AfterUnitLossHealthHelper(
                    damage_message, would_take_damage_message, excess_damage
                )
            else:
                return None
        return None

    @final
    def CanHeath(self) -> bool:
        return self.GetLostHealth() > 0

    @final
    def GetLostHealth(self) -> int:
        return self.max_health - self.health

    # def IsDeath(self) -> bool:
    #     return self.IsDefeated()

    @override
    def IsDefeated(self) -> bool:
        return self.health <= 0 or super().IsDefeated()

    ################################################################################
    #
    @final
    def SetHealth(self, value: int, by_effect: 'Effect') -> None:
        from game.card.face.base import Unit2
        # Send.WhenCardWouldUpdateKeyword_Text(self, value, 'HP', by_effect)
        self.components.health.SetHealth(value)
        if not self.is_infinite_health:
            assert self.health <= self.max_health, f"{self.health=} {self.max_health=}"
        self.LimitHealth(by_effect)

        if Unit2.IsType(self): # Fix "ultron_facedown_drone"
            # Send.WhenCardKeywordUpdated(self, value, 'HP', by_effect)
            message = Message.AfterUnitHitPointSet(self, by_effect)
            message.Send()

    @final
    def GainHealth(self, value: int, by_effect: 'Effect') -> None:
        if self.card.state.is_flipping:
            self.GainOnlyMaxHealth(value, by_effect)
        else:
            self.GainHealthAndMaxHealth(value, by_effect)

    @final
    def GainOnlyMaxHealth(self, value: int, by_effect: 'Effect') -> None:
        # Send.WhenCardWouldUpdateKeyword_Text(self, value, 'MAXHP', by_effect)
        self.UpdateMaxHealth(value, by_effect)
        # Send.WhenCardKeywordUpdated(self, value, 'MAXHP', by_effect)
        # if check_limit:
        #     self.LimitHealth(by_effect)

    @final
    def GainOnlyHealth(self, value: int, by_effect: 'Effect') -> 'Message.AfterUnitHealHealth|Message.AfterUnitLossHealth|None':
        # Send.WhenCardWouldUpdateKeyword_Text(self, value, 'HP', by_effect)
        message = self.UpdateHealth(value, by_effect)
        # if value > 0:
        #     gain_value = diff
        # else:
        #     gain_value = -1 * diff
        # Send.WhenCardKeywordUpdated(self, gain_value, 'HP', by_effect)
        # This line will do `Death` first when deal damage
        # And ultron face down drone will back to a normal player card
        self.LimitHealth(by_effect)
        return message

    @final
    def GainHealthAndMaxHealth(self, value: int, by_effect: 'Effect') -> None:
        if value > 0:
            self.GainOnlyMaxHealth(value, by_effect)
            self.GainOnlyHealth(value, by_effect)
        else:
            self.GainOnlyHealth(value, by_effect)
            self.GainOnlyMaxHealth(value, by_effect)

    @final
    def SetBaseHealth(self, value: int, by_effect: 'Effect') -> None:
        if self.base_health != value:
            diff = value - self.base_health
            self.base_health = value
            self.UpdateMaxHealth(diff, by_effect)
            self.GainOnlyMaxHealth(diff, by_effect)
            self.GainOnlyHealth(diff, by_effect)

    ################################################################################
    #
    @final
    def UpdateMaxHealth(self, value: int, by_effect: 'Effect'):
        self.components.health.AddMaxHealth(value)

    @final
    def UpdateHealth(self, value: int, by_effect: 'Effect', *, max_sustained: int|None=None) -> 'Message.AfterUnitHealHealth|Message.AfterUnitLossHealth|None':
        from game.card.face.base import Unit2
        if not self.IsInPlay():
            return None

        assert Unit2.IsType(self)

        def limit_health(health: int) -> int:
            if max_sustained != None:
                if self.max_health - health > max_sustained:
                    health = self.max_health - max_sustained
            return health

        if value == 0:
            return None
        elif value > 0:
            health = min(self.max_health, self.health + int(value))
            health = limit_health(health)
            value = health - self.health
            if value > 0:
                message = Message.WhenUnitHealHealth(self, value, by_effect)
                message.Send()
                self.components.health.AddHealth(value)
                after_message = Message.AfterUnitHealHealth(self, value, by_effect, message)
                after_message.Send()
                return after_message
            else:
                return None
            # return value
        else:
            message = Message.WhenUnitLossHealth(self, -1 * value, by_effect)
            message.Send()
            health = self.health + int(value)
            health = limit_health(health)
            # We use `Set` to make health can be a negative number
            self.components.health.SetHealth(health)
            after_message = Message.AfterUnitLossHealth(self, -1 * value, message)
            after_message.Send()
            return after_message
            # return -1 * value

    @final
    def LimitHealth(self, by_effect: 'Effect', check_death: bool=True):
        from game.card.face.base import Unit2
        assert Unit2.IsType(self)

        if self.is_infinite_health:
            pass
        elif self.health > self.max_health:
            self.SetHealth(self.max_health, by_effect)
        elif self.health <= 0 and self.IsInPlay() and check_death and not self.card.state.is_leaving_play:
            self.Death(None, by_effect)

    ################################################################################
    #
    @final
    def GainConsideredAtLeastHP(self, diff: int, by_effect: 'Effect') -> None:
        from game.card.face.base import Unit2
        if by_effect not in self.considered_at_least_hp_dict:
            self.considered_at_least_hp_dict[by_effect] = 0
        self.considered_at_least_hp_dict[by_effect] += diff
        if self.health < 0:
            self.Defeated(None, by_effect)
        message = Message.AfterUnitHitPointSet(self.CastTo(Unit2), by_effect)
        message.Send()
