from . import *

# Ionic Physiology


def GetAbilities() -> Sequence['Ability']:

    def sync_attack_after_change_form(effect: 'Effect', message: 'Message.AfterUnitChangeForm') -> None:
        hero = effect.GetInitiator().GetIdentity().GetHeroFace()
        expected = effect.this.GetPlacedCardArea().GetSize()
        current = hero.keywords.get("ATK", {}).get(effect.this, 0)
        hero.GainAttack(expected - current, effect)

    def ionic_physiology(effect: 'Effect', message: 'Message.AfterPlayerPlayedCard') -> None:
        this = effect.this.CastTo(Upgrade)
        if this.TuckCardUnderHere([message.played_face], effect):
            this.HealthUnits([effect.GetInitiator().GetIdentity()], 1, effect)

    return [
        *AbilityFactory.GiveKeywordToInPlayWhenApplyThis(
            "You",
            control_by="You",
            get_new_value=lambda effect, face: effect.this.GetPlacedCardArea().GetSize(),
            attack=1,
            change_on_event=OnEvent.PlacedCard("Here"),
        ),
        AbilityFactory.AfterUnitChangeForm(
            AbilityType.NonKeyword,
            "You",
            sync_attack_after_change_form,
        ),
        AbilityFactory.AfterPlayerPlayedCard(
            AbilityType.Response,
            "You",
            CardFinder(card_type=Event, has_printed_res="Y"),
            ionic_physiology,
            conditions=[
                lambda effect, message: effect.this.GetPlacedCardArea().GetSize() < 3,
                lambda effect, message: message.played_face.card.area == effect.GetInitiator().discard_pile,
            ],
        ),
    ]
