from . import *


def GetAbilities() -> Sequence['Ability']:

    def art_on_villain(effect: 'Effect') -> int:
        villain = Worlds.FindVillain(effect)
        return (
            len(GetArtOn(villain)) * Worlds.GetPlayerNumIcon(effect)
            if villain else 0
        )

    def undefended_attack(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> None:
        player = message.GetToPlayer()
        villain = Worlds.FindVillain(effect)
        art = ChooseArt(player, GetArtOn(message.attacked), effect)
        if villain and art:
            art.AttachTo2(villain, effect)

    return [
        AbilityFactory.WhenCalcThisSchemeEscalation(art_on_villain),
        AbilityFactory.AfterUnitAttackUnitInternal(
            AbilityType.ForcedResponse,
            Enemy,
            Identity,
            undefended_attack,
            is_undefended_attack=True,
        ),
    ]
