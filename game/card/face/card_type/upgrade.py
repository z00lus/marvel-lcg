from core import *
from game.card.face import *
from game.ability import *
from game.message import *
from game.ability.factory import *
from game.player import *
from game.element.damage_property import DamageProperty

@final
class Upgrade(Asset2, HasTeamUp, HasModify, HasForm, HasRestricted, HasUses, HasHazard, HasAmplify, CanCrisis, HasPermanent, HasTemporary, HasSetup, HasVictory, ClassCard, FinalType):
    @override
    def GetAbilities(self) -> List['Ability']:
        abilities: List['Ability'] = []
        play_ability = None
        if not self.ability.Find(func_name="Play"):
            play_ability = AbilityFactory.CanPlayThisUpgradeCard()
            abilities.append(play_ability)
        else:
            play_abilities = self.ability.Find(func_name="Play")
            if play_abilities:
                play_ability = play_abilities[0]
        if play_ability and play_ability.selectors and play_ability.selectors[0]:
            def check_condition(effect: 'Effect', message: 'Message2') -> bool:
                for condition in play_ability.const_condition:
                    if not condition(effect, message):
                        return False
                return True

            abilities.append(
                AbilityFactory.AttachToFaceWhenPutIntoPlayInternal(
                    play_ability.selectors[0],
                    conditions=[check_condition]
                )
            )
        return abilities + super().GetAbilities()

    # @override
    # def OnPutIntoPlay(self, player: 'Player', by_effect: 'Effect') -> 'bool':
    #     from game.card.face.faces import Faces

    #     play_effects = self.effect.FindEffects(func_name="Play")
    #     assert len(play_effects) == 1, f"{self=}"
    #     play_effect = play_effects[0]
    #     face = player.GetIdentity()
    #     if play_effect.ability.selector:
    #         face = player.AskChooseOneSelect(play_effect.ability.selector, by_effect)

    #     if face:
    #         self.AttachTo2(face, by_effect)
    #     else:
    #         Faces.DiscardAll([self], by_effect)
    #         return False
    #     return super().OnPutIntoPlay(player, by_effect)

    def GetControlByOrOwnerFace(self) -> 'CardFace':
        bind_card = self.card.area.bind_card
        if bind_card == None:
            bind_card = self.card.area.GetOwner().GetRoleCharacter().card
        controller = bind_card.GetController()
        if not controller or not controller.IsPlayer():
            return self.GetOwnerPlayer().GetIdentity()
        else:
            return bind_card.face

    @override
    def OnDealDamage(self, units: List['Unit2'], damage: 'int|DamageProperty', by_effect: 'Effect', *, property: 'AttackProperty|None'=None, attack_in_event: bool) -> int|None:
        assert by_effect != None, f"{self=}"
        assert self == by_effect.this, f"{self=} {by_effect.this=}"

        identity = self.GetControlByOrOwnerFace()
        if identity.IsDefeated():
            return None
        return identity.OnDealDamage(units, damage, by_effect, property=property, attack_in_event=attack_in_event)

    @override
    def OnRemoveSchemeThreat(self, schemes: List['Scheme2'], value: int, by_effect: 'Effect') -> int|None:
        assert by_effect != None, f"{self=}"
        assert self == by_effect.this, f"{self=} {by_effect.this=}"

        hero = self.GetControlByOrOwnerFace()
        return hero.OnRemoveSchemeThreat(schemes, value, by_effect)

    @override
    def CanAttachTo(self, face: 'CardFace') -> bool:
        if not super().CanAttachTo(face):
            return False
        play_abilities = self.ability.Find(func_name="Play")
        for ability in play_abilities:
            assert ability.selectors
            if ability.selectors[0] and \
                ability.selectors[0].target_text and \
                ability.selectors[0].target_text != "TeamUp" and \
                not isinstance(face, CardFinderHelper.GetTargetType(ability.selectors[0].target_text)):
                return False
            if ability.selectors[0]:
                return ability.selectors[0].selector_filter.CheckFinder(face, None)
            else:
                return True
        return False
        # play_abilities = upgrade.FindAbilities(func_name="Play")
        # for ability in play_abilities:
        #     if ability.selector and ability.selector.FilterLegalTargets([ally], effect):
        #         return True
        # return False
