from . import *


def GetAbilities() -> Sequence['Ability']:

    def embody_pathos_revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Attachment)
        player = message.GetToPlayer()
        scheme = Find.Find(
            effect,
            who_perform=player,
            finder=CardFinder(
                card_type=EncounterSideScheme,
                check_face_fn=lambda face: not face.IsInPlay(),
            ),
        )
        if not scheme:
            Faces.DiscardAll([this], effect)
            return

        def one_player_value(key: str) -> int:
            printed = scheme.paper.desc.get(key, "0")
            return int(printed[:-1]) if printed.endswith("*") else int(printed)

        player_num = effect.world.started_player_num
        start_threat = scheme.start_threat
        printed_hinder = scheme.printed_hinder
        one_player_hinder = one_player_value("Hinder")
        try:
            # Embody Pathos treats every per-hero icon on the revealed
            # scheme as 1, including icons resolved by its scripted ability.
            effect.world.started_player_num = 1
            scheme.start_threat = one_player_value("StartingThreat")
            scheme.printed_hinder = one_player_hinder
            scheme.Reveal(player, effect)
        finally:
            effect.world.started_player_num = player_num
            scheme.start_threat = start_threat
            scheme.printed_hinder = printed_hinder
            if scheme.IsInPlay():
                scheme.GainHinder(printed_hinder - one_player_hinder, effect)

        if scheme.IsInPlay():
            this.AttachTo2(scheme, effect)
            this.PlaceThreatOnSchemes([scheme], 6, effect)
        else:
            Faces.DiscardAll([this], effect)

    def not_hercules_thwart(effect: 'Effect', message: 'Message.WhenSchemeWouldRemoveThreat') -> bool:
        return not (
            message.would_thw_message is not None and
            message.by_face.IsName("Hercules", check_all_face=True)
        )

    def complete_labor(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        Faces.AddToVictoryDisplay([effect.this], effect)

    return [
        ReturnLaborToDeckWhenItLeavesPlay(),
        AbilityFactory.WhenThisRevealed(None, embody_pathos_revealed),
        *AbilityFactory.GiveKeywordToAttached(
            EncounterSideScheme,
            assault=1,
        ),
        AbilityFactory.ThreatCannotBeRemovedFromWhile(
            "AttachedScheme",
            conditions=[not_hercules_thwart],
        ),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.Interrupt,
            "AttachedScheme",
            complete_labor,
        ),
    ]
