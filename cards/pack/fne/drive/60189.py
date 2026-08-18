from . import *


def GetAbilities() -> Sequence['Ability']:
    vehicle_character = CardFinder(
        card_type=Unit2,
        with_attach=CardFinder(
            trait="VEHICLE",
            card_type=Attachment,
        ),
    )

    def redirect_placed_threat(
        effect: 'Effect',
        message: 'Message.WhenCardWouldBePlacedToken',
    ) -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        message.SetBeInstead(effect)
        this.PlaceThreatOnSchemes([this], message.num, effect)

    def redirect_removed_threat(
        effect: 'Effect',
        message: 'Message.WhenCardWouldRemovedToken',
    ) -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        value: int|Literal["All"] = (
            "All" if message.remove_all else message.would_remove or 0
        )
        message.SetBeInstead(effect)
        if value:
            this.RemoveThreatFromSchemes([this], value, effect)

    def is_vehicle_character(
        effect: 'Effect',
        message: 'Message.WhenCardWouldBePlacedToken|Message.WhenCardWouldRemovedToken',
    ) -> bool:
        # The token message is triggered by the scheme receiving/losing threat.
        # The character responsible for that change is the source of the bound
        # effect, not message.trigger.
        return (
            message.token_name == 'threat'
            and vehicle_character.Check(message.by_effect.this, effect)
        )

    return [
        AbilityFactory.WhenCardWouldBePlacedToken(
            AbilityType.ForcedInterrupt,
            Scheme2,
            'threat',
            redirect_placed_threat,
            conditions=[is_vehicle_character],
        ),
        Ability(
            AbilityType.ForcedInterrupt,
            Message.WhenCardWouldRemovedToken,
            [is_vehicle_character],
            redirect_removed_threat,
        ),
    ]
