from cards.pack import *


KINGPIN = CardFinder(name="Kingpin", card_type=Villain)
PUBLIC_SUPPORT = CardFinder(name="Public Support", card_type=Environment)


def FindNemesisMinion(effect: 'Effect', player: 'Player') -> 'Minion|None':
    return Search.EncounterCard(
        effect,
        player,
        include_discard_pile=True,
        include_set_aside=True,
        card_type=Minion,
        is_nemesis=player,
    )


def FindAndRevealUnderling(effect: 'Effect', player: 'Player') -> 'Minion|None':
    minion = Search.EncounterCard(
        effect,
        player,
        include_discard_pile=True,
        include_set_aside=True,
        card_type=Minion,
        trait="UNDERLING",
    )
    if minion:
        minion.Reveal(player, effect)
    return minion


def RevealNemesisOrUnderling(effect: 'Effect', player: 'Player') -> None:
    minion = FindNemesisMinion(effect, player)
    if not minion:
        FindAndRevealUnderling(effect, player)
        return

    entered = [False]
    minion.Reveal(
        player,
        effect,
        if_entered_play=lambda: entered.__setitem__(0, True),
    )
    if not entered[0]:
        FindAndRevealUnderling(effect, player)


def GetKingpinLowSupportAbilities() -> Sequence['Ability']:
    def scheme_instead(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        message.DoSchemeInstead(effect)

    return [
        AbilityFactory.ThisCannotTakeDamageWhile(conditions=True),
        *AbilityFactory.UnitCannotHaveUpgradeAttached("This"),
        AbilityFactory.WhenUnitWouldAttack(
            AbilityType.ForcedInterrupt,
            "This",
            scheme_instead,
        ),
    ]


def GetKingpinHighSupportAbilities(expert: bool) -> Sequence['Ability']:
    def activate(effect: 'Effect', message: 'Message.WhenEnemyWouldActivate') -> None:
        player = message.GetToPlayer()
        if player.engaged_minions.GetSize() == 0:
            message.GiveBoostCardForThisActivation(1, effect)

    def overkill(effect: 'Effect', message: 'Message.WhenEnemyActivateAgainstYou') -> None:
        if isinstance(message.would_message, Message.WhenUnitWouldAttack):
            message.would_message.GainOverKill(effect)

    abilities: List['Ability'] = [
        AbilityFactory.WhenEnemyWouldActivate(
            AbilityType.ForcedInterrupt,
            "This",
            activate,
        ),
    ]
    if expert:
        abilities.append(
            AbilityFactory.WhenEnemyActivateAgainstYou(
                AbilityType.ForcedInterrupt,
                "This",
                overkill,
            )
        )
    return abilities


def PublicSupportCounterAbility() -> 'Ability':
    def place_counter(effect: 'Effect', message: 'Message.AfterUnitBeDefeated') -> None:
        Faces.PlaceCountersOn([effect.this], 1, 'support', effect)

    return AbilityFactory.AfterUnitBeDefeated(
        AbilityType.ForcedResponse,
        Minion,
        place_counter,
    )
