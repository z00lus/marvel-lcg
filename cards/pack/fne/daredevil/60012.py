from . import *

# * Focus the Senses


def GetAbilities() -> Sequence['Ability']:

    def is_not_daredevil_or_matt(effect: 'Effect', message: 'Message.WhenSchemeWouldRemoveThreat') -> bool:
        return not (
            message.by_face.IsName("Daredevil") or
            message.by_face.IsName("Matt Murdock")
        )

    def focus_the_senses(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        player = effect.GetInitiator()
        senses_in_play = effect.world.FindCardsOnField(
            finder=CardFinder(trait="SENSE"),
            owner=player,
        )
        selected = player.AskChooseFaces(
            senses_in_play,
            (0, len(senses_in_play)),
            effect,
            prompt="Choose Sense upgrades to move",
            forced=False,
        )
        for sense in selected:
            targets = [
                face for face in Worlds.GetOnFieldCards(effect)
                if face != sense.GetBindFace() and sense.CanAttachTo(face)
            ]
            target = player.MayChooseFace(targets, effect, not_move=True)
            if target:
                sense.AttachTo2(target, effect)

        deck = GetSenseDeck(player)
        if not deck:
            return
        deck_senses = deck.GetAll(from_top=True, include_removed=False)
        selected = player.AskChooseFaces(
            deck_senses,
            (0, len(deck_senses)),
            effect,
            prompt="Choose Sense upgrades to put into play",
            forced=False,
        )
        for sense in selected:
            sense.PutIntoPlay(player, effect, under_control=True)

    return [
        AbilityFactory.CanPlayThisSchemeCard(),
        AbilityFactory.ThreatCannotBeRemovedFromWhile(
            "This",
            conditions=[is_not_daredevil_or_matt],
        ),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            focus_the_senses,
        ),
    ]
