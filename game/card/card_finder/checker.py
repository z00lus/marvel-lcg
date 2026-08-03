from core import *

from game.effect import *
from game.card.face import *
from game.world.game_area import *
from game.player import *

from game.element.resources import Resources

from game.card.face.attribute.has_hazard import HasHazard
from game.card.face.attribute.has_amplify import HasAmplify
from game.card.face.attribute.has_crisis import CanCrisis
from game.card.face.attribute.has_acceleration_icon import HasAccelerationIcon
from game.card.face.attribute.can_place_counter import CanPlaceCounter
from game.card.face.attribute.can_place_token import CanPlaceToken
from game.card.face.attribute.has_cost import HasCost
from game.card.face.attribute.has_permanent import HasPermanent
from game.card.face.attribute.has_temporary import HasTemporary
from game.card.face.attribute.has_form import HasForm
from game.card.face.attribute.has_stage import HasStage
from game.card.face.attribute.can_attach import CanAttach
from game.card.face.base import ClassCard
from game.card.face.base import Scheme2
from game.card.face.base import Unit2
from game.card.face.base import Asset2
from game.card.face.base import Villain
from game.card.face.card_type import Minion
# from game.card.face.card_type import Upgrade
from game.card.face.card_type import Identity
from game.card.face.card_type import Obligation
# from game.ability.ability_type import AbilityType
from game.player import Player

@Tracker.count_calls
def Check(self: 'CardFinder', face: 'CardFace', effect: 'Effect|None'=None) -> bool:
    assert not self.is_empty

    if self.or_finders:
        for finder in self.or_finders:
            if finder.Check(face, effect):
                return True

    ################################################################################
    # Name
    if self.name != None:
        if not face.IsName(self.name) and not face.IsSubName(self.name):
            return False
    if self.names != []:
        if not any(face.IsName(name) or face.IsSubName(name) for name in self.names):
            return False
    if self.non_name != None:
        if face.IsName(self.non_name) or face.IsSubName(self.non_name):
            return False
    if self.subtitle != None:
        if not face.IsName(self.subtitle) and not face.IsSubName(self.subtitle):
            return False
    if self.card_ids != []:
        if face.paper.card_id not in self.card_ids:
            return False
    if self.title_contain != None:
        if not face.TitleContain(self.title_contain):
            return False
    if self.non_face != None:
        if face == self.non_face:
            return False
    if self.with_texts != []:
        def check_text():
            assert self.with_texts != None
            for text in self.with_texts:
                if text == "Hero Action":
                    for ability in face.ability.abilities:
                        if ability.flags.is_hero_action:
                            return True
                if text == "Hero Response":
                    for ability in face.ability.abilities:
                        if ability.flags.is_hero_response:
                            return True
            return False
        if not check_text():
            return False
    if self.subtype != None:
        if not Evidence.IsType(face):
            return False
        if face.subtype != self.subtype:
            return False
    ################################################################################
    # Set
    if self.set_name != None:
        if self.set_name != face.paper.set_name:
            return False
    if self.non_set_name != None:
        if self.non_set_name == face.paper.set_name:
            return False
    # def check_packs(effect: 'Effect|None', face: 'CardFace') -> Literal[False]|None:
    #     # if packs != None and face.paper.pack not in packs:
    #         return False
    ################################################################################
    # Trait
    if self.trait != None:
        if not face.HasTrait(self.trait):
            return False
    if self.traits != []:
        if not face.HasTrait(*self.traits):
            return False
    if self.non_trait != None:
        if face.HasTrait(self.non_trait):
            return False
    if self.share_trait != None:
        if not face.ShareTrait(self.share_trait):
            return False
    ################################################################################
    # Class
    if self.card_class != None:
        if not ClassCard.IsType(face) or not face.IsClass(self.card_class):
            return False
    if self.card_classes != []:
        if not ClassCard.IsType(face) or not face.IsClass(*self.card_classes):
            return False
    if self.deck_building_class != None:
        if not ClassCard.IsType(face) or not face.IsDeckBuildingClass(self.deck_building_class):
            return False
    ################################################################################
    # Type
    if self.card_type != None:
        if not face.IsTypeOld(self.card_type):
            return False
    if self.non_card_type != None:
        if face.IsTypeOld(self.non_card_type):
            return False
    if self.form != None:
        if not HasForm.IsType(face):
            return False
        if self.form != face.form:
            return False
    ################################################################################
    # Normal
    if self.is_unique != None:
        if self.is_unique != face.IsUnique():
            return False
    if self.is_permanent != None:
        if HasPermanent.IsType(face) and self.is_permanent != face.permanent:
            return False
    if self.is_face_up != None:
        if face.IsFaceUp() != self.is_face_up:
            return False
    if self.is_temporary != None:
        if not isinstance(face, HasTemporary):
            return False
        if self.is_temporary != face.temporary:
            return False
    if self.canbe_play != None:
        if effect == None:
            return False
        if effect.this.paper.card_id == face.paper.card_id:
            return False
        initiator = effect.GetInitiator()
        return self.canbe_play == face.CanPlayBy(initiator)
    if self.canbe_exhaust != None:
        if self.canbe_exhaust != face.CanExhaust():
            return False
    if self.canbe_ready != None:
        if self.canbe_ready != face.CanReady():
            return False
        if effect != None:
            if self.canbe_ready != face.IsCanReadyBy(effect):
                return False
    if self.canbe_flip != None:
        pass
    if self.canbe_discard != None:
        if (HasPermanent.IsType(face) and face.permanent) or Identity.IsType(face):
            return False
        if self.canbe_discard and getattr(face, "cannot_choose_discard", False):
            return False
    ################################################################################
    # Game Area
    if self.game_area != None:
        if self.game_area != face.card.GetGameArea():
            return False
    ################################################################################
    # Unit
    if self.canbe_heal != None:
        if not Unit2.IsType(face) or self.canbe_heal != face.CanHeath():
            return False
    if self.sustained != None:
        if not Unit2.IsType(face) or self.sustained != face.sustained:
            return False
    #     #  if has_health != None:
    #     #     if not Unit2.IsType(face) or face.health <= 0:
    #     return False
    if self.has_non_health != None:
        if not Unit2.IsType(face):
            return False
        if self.has_non_health != bool(face.health <= 0):
            return False
    if self.with_health != None:
        if not Unit2.IsType(face) or face.health != self.with_health:
            return False
    ################################################################################
    # Status
    if self.with_tough != None:
        if not Unit2.IsType(face) or self.with_tough != face.IsTough():
            return False
    if self.is_confused != None:
        if not Unit2.IsType(face) or self.is_confused != face.IsConfused():
            return False
    if self.has_confuse_status != None:
        if not Unit2.IsType(face) or face.confused <= 0:
            return False
    if self.is_stunned != None:
        if not Unit2.IsType(face) or self.is_stunned != face.IsStunned():
            return False
    # if self.has_any_status != None:
    #     if not Unit2.IsType(face) or self.has_any_status != (face.IsTough() or face.IsConfused() or face.IsStunned()):
    #         return False
    if self.canbe_tough != None:
        if not Unit2.IsType(face) or self.canbe_tough != face.CanGainTough():
            return False
    if self.canbe_stunned != None:
        if not Unit2.IsType(face) or self.canbe_stunned != face.CanbeStunned():
            return False
    if self.canbe_confused != None:
        if not Unit2.IsType(face) or self.canbe_confused != face.CanbeConfused():
            return False
    if self.has_status:
        if not Unit2.IsType(face):
            return False
        if self.has_status == "Any":
            check_status = ["Confused", "Stunned", "Tough"]
        elif not isinstance(self.has_status, list):
            check_status = [self.has_status]
        else:
            check_status = self.has_status
        is_has_status = False
        for staus in check_status:
            if staus == "Confused" and face.IsConfused():
                is_has_status = True
                break
            if staus == "Tough" and face.IsTough():
                is_has_status = True
                break
            if staus == "Stunned" and face.IsStunned():
                is_has_status = True
                break
        if not is_has_status:
            return False
    if self.canbe_status:
        if not Unit2.IsType(face):
            return False
        if self.canbe_status == "Any":
            check_status = ["Confused", "Stunned", "Tough"]
        elif not isinstance(self.canbe_status, list):
            check_status = [self.canbe_status]
        else:
            check_status = self.canbe_status
        is_canbe_status = False
        for staus in check_status:
            if staus == "Confused" and face.CanbeConfused():
                is_canbe_status = True
                break
            if staus == "Tough" and face.CanGainTough():
                is_canbe_status = True
                break
            if staus == "Stunned" and face.CanbeStunned():
                is_canbe_status = True
                break
        if not is_canbe_status:
            return False

    ################################################################################
    # Asset
    if self.canbe_attach_by != None:
        if Asset2.IsType(self.canbe_attach_by):
            if not self.canbe_attach_by.CanAttachTo(face):
                return False
    if self.canbe_attach_to != None:
        if Asset2.IsType(face):
            if not face.CanAttachTo(self.canbe_attach_to):
                return False
    ################################################################################
    # Scheme
    if self.has_threat != None:
        if not Scheme2.IsType(face) or face.threat <= 0:
            return False
    ################################################################################
    # Villain / Minion / Obligation
    if self.is_active_villain != None:
        if not Villain.IsType(face) or self.is_active_villain != face.IsActive():
            return False
    if self.stage != None:
        if not HasStage.IsType(face) or self.stage != face.printed_stage:
            return False
    if self.is_nemesis != None:
        if EncounterSideScheme.IsType(face):
            if isinstance(self.is_nemesis, Player):
                if not face.IsNemesis(self.is_nemesis):
                    return False
            elif self.is_nemesis != face.paper.set_name.endswith(" Nemesis"):
                return False
        elif Minion.IsType(face):
            if isinstance(self.is_nemesis, Player):
                if not face.IsNemesis(self.is_nemesis):
                    return False
            elif self.is_nemesis == True and face.nemesis == "" :
                return False
            elif self.is_nemesis == False and face.nemesis != "" :
                return False
        else:
            return False
    if self.engaged_with != None:
        if not Minion.IsType(face):
            return False
        if face.engaged_player == None:
            return False
        elif isinstance(self.engaged_with, Player):
            if self.engaged_with != face.engaged_player:
                return False
        elif not self.engaged_with.Check(face.engaged_player.GetIdentity()):
            return False
    if self.not_engaged_with != None:
        if not Minion.IsType(face):
            return False
        if self.not_engaged_with == face.engaged_player:
            return False
    if self.obligation_give_to != None:
        if not Obligation.IsType(face):
            return False
        if not self.obligation_give_to.IsName(face.give_to):
            return False
    ################################################################################
    # Icons
    if self.amplify != None:
        if not HasAmplify.IsType(face) or self.amplify != bool(face.amplify):
            return False
    if self.crisis != None:
        if not CanCrisis.IsType(face) or self.crisis != bool(face.crisis):
            return False
    if self.acceleration_icon != None:
        if not HasAccelerationIcon.IsType(face) or self.acceleration_icon != bool(face.acceleration_icon):
            return False
    if self.acceleration_token != None:
        if not CanAccelerationToken.IsType(face) or self.acceleration_token != bool(face.acceleration_token):
            return False
    if self.hazard != None:
        if not HasHazard.IsType(face) or self.hazard != bool(face.hazard):
            return False
    ################################################################################
    # Counter / Token
    if self.has_counter != None:
        if not isinstance(face, CanPlaceCounter):
            return False
        if face.GetCounters(self.has_counter) == 0:
            return False
    if self.has_token != None:
        if not isinstance(face, CanPlaceToken) or face.GetTokens(self.has_token) == 0:
            return False
    ################################################################################
    # Attach
    if self.has_attach != None:
        faces = face.GetInventoryDeck().Get()
        is_has_attach = False
        for attach in faces:
            if self.has_attach.Check(attach, effect):
                is_has_attach = True
                break
        if not is_has_attach:
            return False
    if self.attach_to != None:
        if Asset2.IsType(face):
            if face.bind_face == None:
                return False
            if not self.attach_to.Check(face.bind_face, effect):
                return False
    if self.with_attach != None:
        deck = face.GetInventoryDeck()
        if isinstance(self.with_attach, bool):
            if self.with_attach == True and deck.GetSize() == 0:
                return False
            elif self.with_attach == False and deck.GetSize() != 0:
                return False
        elif isinstance(self.with_attach, CardFinder):
            if deck.FindCard(
                card_type=CanAttach,
                finder=self.with_attach,
            ) == None:
                return False
        else:
            if deck.FindCardSize(CardFinder(card_type=self.with_attach)) == 0:
                return False
    if self.not_with_attach != None:
        deck = face.GetInventoryDeck()
        if isinstance(self.not_with_attach, CardFinder):
            if deck.FindCard(
                card_type=CanAttach,
                finder=self.not_with_attach,
            ) != None:
                return False
        else:
            if deck.FindCardSize(CardFinder(card_type=self.not_with_attach)) != 0:
                return False
    if self.bind_to != None:
        if isinstance(self.bind_to, CardFinder):
            if not self.bind_to.Check(face.GetBindFace(), effect):
                return False
        else:
            if self.bind_to != face.GetBindFace():
                return False
    ################################################################################
    # Cost
    if self.cost_less_than != None:
        if not HasCost.IsType(face):
            return False
        if face.printed_cost.val > self.cost_less_than:
            return False
    if self.cost_equal_or_greater != None:
        if not HasCost.IsType(face):
            return False
        if face.printed_cost.val < self.cost_equal_or_greater:
            return False
    if self.cost_equal_or_less != None:
        if not HasCost.IsType(face):
            return False
        if face.printed_cost.val > self.cost_equal_or_less:
            return False
    ################################################################################
    # Res
    if self.has_printed_res != None:
        if not ClassCard.IsType(face):
            return False
        if Identity.IsType(face):
            return False
        test_printed_reses: List["Resources.RBYG"] = []
        if self.has_printed_res == True:
            test_printed_reses = Resources.RBYG_LIST
        elif isinstance(self.has_printed_res, list):
            test_printed_reses = self.has_printed_res
        else:
            test_printed_reses = [self.has_printed_res]
        if not face.printed_resource.HasOneOfColor(test_printed_reses, convert_green_res=False):
            return False
    if self.non_printed_res != None:
        if not ClassCard.IsType(face):
            return False
        if face.printed_resource.HasColorPrinted(self.non_printed_res):
            return False
    if self.with_res != None:
        if Identity.IsType(face):
            return False
        if not ClassCard.IsType(face):
            return False
        if not face.printed_resource.HasColor(self.with_res):
            return False
    ################################################################################
    # Owner
    if self.owner != None:
        if face.GetOwner() != self.owner:
            return False
    #   if control_by_player != None:
    #     if not face.GetControlBy().IsPlayer():
    #         return False
    # finder.control_by_player  : Final = control_by_player
    ################################################################################
    # Other
    if self.is_scenario_specific != None:
        if self.is_scenario_specific == True:
            if effect:
                return face.paper.card_id in effect.world.scene.campaign.encounters
        else:
            if effect:
                return face.paper.card_id not in effect.world.scene.campaign.encounters
    if self.not_has_that_unique_in_play != None:
        if face.card.world.IsThisUniqueInPlay(face):
            return False
    ################################################################################
    #
    if self.check_face_fns != []:
        for check_face_fn in self.check_face_fns:
            if not check_face_fn(face):
                return False
    if self.check_effect_fns != []:
        if effect:
            for check_effect_fn in self.check_effect_fns:
                if not check_effect_fn(effect, face):
                    return False
    return True

@Tracker.count_calls
def Checks(self: 'CardFinder', faces: Sequence['CardFace'], effect: 'Effect|None'=None) -> Sequence['CardFace']:
    assert not self.is_empty

    checked: List['CardFace'] = []
    for face in faces:
        if self.Check(face, effect):
            checked.append(face)

    return checked

def Checks2(self: 'CardFinder', faces: Sequence['CardFace'], card_type: Type[TF]) -> List['TF']:
    faces = self.Checks(faces)
    return [x for x in faces if card_type.IsType(x)]
