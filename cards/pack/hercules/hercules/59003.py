from . import *


def GetAbilities() -> Sequence['Ability']:

    def embody_pathos_revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Attachment)
        player = message.GetToPlayer()
        scheme = Find.FindAndReveal(
            effect,
            player,
            finder=CardFinder(
                card_type=EncounterSideScheme,
                check_face_fn=lambda face: not face.IsInPlay(),
            ),
        )
        if scheme:
            def one_player_value(key: str) -> int:
                printed = scheme.paper.desc.get(key, "0")
                return int(printed[:-1]) if printed.endswith("*") else int(printed)

            scheme.SetTokens(
                one_player_value("StartingThreat") + one_player_value("Hinder"),
                "threat",
                effect,
            )
            this.AttachTo2(scheme, effect)
            this.PlaceThreatOnSchemes([scheme], 6, effect)

    def not_hercules_thwart(effect: 'Effect', message: 'Message.WhenSchemeWouldRemoveThreat') -> bool:
        return not (
            message.would_thw_message is not None and
            message.by_face.IsName("Hercules", check_all_face=True)
        )

    def complete_labor(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        Faces.AddToVictoryDisplay([effect.this], effect)

    return [
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
