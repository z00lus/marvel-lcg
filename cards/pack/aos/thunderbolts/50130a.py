from . import *
from cards.pack.aos.campaign import CampaignSetup

# Apprehending Rogue Agents

def GetAbilities() -> Sequence['Ability']:

    def apprehending_rogue_agents_sets(effect: 'Effect', message: 'Message.WhenGameBeginSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        # We don't check `with an [[Elite]], [[Thunderbolt]] minion`, handle it yourself
        choose_sets = [
            x for x in message.encounter_set_names
            if not x.startswith('expert') and not x.startswith('standard')
        ]

        size = Worlds.GetPlayerNumIcon(effect) + 1

        message.encounter_set_names = [x for x in message.encounter_set_names if x not in choose_sets] + Rand.RandomChoice2(choose_sets, size, effect)

    def apprehending_rogue_agents(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        SetupCards.SetAsideCards(
            effect,
            card_type=Minion,
            check_face_fn=lambda face:
                face.HasTrait("ELITE") and \
                face.HasTrait("THUNDERBOLT") and \
                face.paper.set_name != "Thunderbolts"
        )

        SetupCards.Reveal(
            effect,
            name="Justice, Like Lightning",
            card_type=Environment
        )


    return [
        AbilityFactory.WhenGameBeginSetup(
            apprehending_rogue_agents_sets
        ),
        AbilityFactory.WhenCardSetup(
            "This",
            apprehending_rogue_agents
        ),
        *CampaignSetup(4),
    ]
