from game.card.face import *
from game.effect import *
from game.player import *
from game.card.face.model.base import ModelBase

class ModelForm(ModelBase):
    def DefaultChangeToFace(self, to_form: 'AlterEgo|Hero|Villain', by_effect: 'Effect') -> bool:
        from game.card.face.base import Unit2
        from game.message import Message

        this = self.GetThis().CastTo(Unit2)
        if this == to_form:
            return True

        if not this.card.world.is_game_started:
            assert False
            return this.FlipTo(by_effect, card_face=to_form)
        # if this.paper.card_id.startswith("3100"):
        #     # player.GetIdentity().FlipTo(effect, name=face.name)
        else:
            would_message = Message.WhenUnitWouldChangeForm(this, to_form, False, by_effect)
            would_message.Send()
            if would_message.is_be_instead:
                return False
            if to_form in this.card.back_faces:
                this.FlipTo(by_effect, card_face=to_form)
            else:
                # player = this.GetControlByPlayer()
                # health = this.health
                this.FlipTo(by_effect, card_face=this.card.back_faces[0])
                # to_form.FlipTo(by_effect, card_face=to_form)
                # to_form.PutIntoPlay(player, by_effect, under_control=True)
                # to_form.SetHealth(health, by_effect)

            # Identity form can be part of a dynamic permission to play a
            # tucked card.  Do not retain the result calculated for the old
            # form after the identity flips.
            for face in to_form.GetPlacedCardArea().GetAll():
                face.card.can_state.is_like_in_hand = None

            after_message = Message.AfterUnitChangeForm(to_form, None, by_effect, would_message)
            after_message.Send()
            end_message = Message.AfterUnitChangeFormEnd(to_form, by_effect, after_message)
            end_message.Send()
            return True

    def DefaultChangeToForm(self, finder: 'CardFinder', by_effect: 'Effect'):
        from game.card.face.base import Villain
        from game.player import Player
        this = self.GetThis()

        if finder.Check(this):
            return

        player = this.GetControlBy()
        if Player.IsType(player):
            faces: List['AlterEgo|Hero'] = player.GetAllIdentityFace()
            faces = [face for face in faces if finder.Check(face)]
            if len(faces) > 0:
                face_dict: Dict[str, 'AlterEgo|Hero'] = {}
                for face in faces:
                    name = face.traits_str
                    face_dict[name] = face
                face_name = player.AskChooseOneText([x for x in face_dict])
                face = face_dict[face_name]
            else:
                face = faces[0]
            this.DefaultChangeToFace(face, by_effect)
            return
        else:
            face = self.GetThis()
            for check_face in [face] + face.card.back_faces:
                if finder.Check(check_face):
                    assert Villain.IsType(check_face)
                    this.DefaultChangeToFace(check_face, by_effect)
                    return

        assert False, f"{this=} {by_effect=}"

