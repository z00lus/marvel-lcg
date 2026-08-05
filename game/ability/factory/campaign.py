from . import *

class AbilityFactoryCampaign:

    @staticmethod
    def WhenCampaignSetup(operation: OperationType[Message.WhenCampaignSetup],
                        *,
                        conditions: ConditionsType[Message.WhenCampaignSetup]=[],
                        campaign_id: str|None=None,
                        ) -> 'Ability':
        from game.operate.worlds import Worlds
        return Ability(
            AbilityType.Campaign,
            Message.WhenCampaignSetup,
            [
                lambda effect, message:
                    Worlds.IsCampaign(effect) and (
                        campaign_id == None or
                        Worlds.IsCampaignSelected(effect, campaign_id)
                    ),
                *conditions
            ],
            operation
        )

    @staticmethod
    def WhenCampaignSetupExpertOnly(operation: OperationType[Message.WhenCampaignSetup],
                                    *,
                                    conditions: ConditionsType[Message.WhenCampaignSetup]=[],
                                    campaign_id: str|None=None,
                                    ) -> 'Ability':
        from game.operate.worlds import Worlds
        return AbilityFactoryCampaign.WhenCampaignSetup(
            operation,
            conditions=[
                lambda effect, message:
                    Worlds.IsExpert(effect),
                *conditions
            ],
            campaign_id=campaign_id,
        )

    @staticmethod
    def CampaignSetPlayersHPToTheirRemainingHP(*, campaign_id: str|None=None) -> 'Ability':
        from game.operate.worlds import Worlds
        from game.operate.campaign_logs import CampaignLog
        def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
            for player in Worlds.GetPlayers(effect):
                player_id = player.player_id
                value = CampaignLog.GetIntByPlayer("Remaining hit points", player_id, effect)
                if value:
                    player.GetIdentity().SetHealth(value, effect)

        return AbilityFactoryCampaign.WhenCampaignSetup(
            action,
            campaign_id=campaign_id,
        )

    @staticmethod
    def ExpertCampaignSetPlayersHPToTheirRemainingHP(*, campaign_id: str|None=None) -> 'Ability':
        # Compatibility alias for campaign modules written before remaining hit
        # points were supported in both standard and expert campaign games.
        return AbilityFactoryCampaign.CampaignSetPlayersHPToTheirRemainingHP(
            campaign_id=campaign_id,
        )

    @staticmethod
    def PutCardIntoPlay(card_id: str, under_control: Literal["FirstPlayer"]|None=None, *, campaign_id: str|None=None) -> 'Ability':
        from game.card.factory import CardFactory
        def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
            card = CardFactory.GenerateCard(card_id, None, effect.world)
            face = card.face
            face.PutIntoPlay("FirstPlayer", effect, under_control=under_control != None)
        return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=campaign_id)

    @staticmethod
    def ShuffleCardIntoDeck(card_id: str, deck: Literal["EncounterDeck"], *, campaign_id: str|None=None) -> 'Ability':
        from game.card.factory import CardFactory
        from game.operate.faces import Faces
        def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
            card = CardFactory.GenerateCard(card_id, None, effect.world)
            Faces.ShuffleAllTo([card.face], deck, effect)
        return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=campaign_id)

    @staticmethod
    def ChooseCardAtRandomAndShuffleIntoEncounterDeck(card_ids: List[str], *, campaign_id: str|None=None) -> 'Ability':
        from game.card.factory import CardFactory
        from engine.lib import Random
        from game.operate.campaign_logs import CampaignLog
        from game.operate.faces import Faces
        def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
            checked_ids = CampaignLog.GetList("Community Service: Victory for Scenarios #1-4", effect)
            card_id = Random.RandomChoice([x for x in card_ids if x not in checked_ids])
            card = CardFactory.GenerateCard(card_id, None, effect.world)
            Faces.ShuffleAllTo([card.face], "EncounterDeck", effect)
        return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=campaign_id)

    @staticmethod
    def ExpertCampaignEachPlayerMayDealFacedownEncounterCardYpHealHP(size: int, *, campaign_id: str|None=None) -> 'Ability':
        from game.operate.worlds import Worlds
        from game.ability.factory import AbilityFactory
        def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
            this = effect.this

            for player in Worlds.GetPlayers(effect):
                def action(targets: Sequence['CardFace']):
                    player.DealEncounterCards(size, effect)
                    this.HealthUnits(targets, "All", effect)

                player.MayChooseOneAbility(
                    effect,
                    AbilityFactory.ForChoiceAbility(
                        f"may deal themself {size} facedown encounter card from the encounter deck to set their hit point dial to their identity's printed hit point value",
                        action,
                    ).SetTarget([player.GetIdentity()], canbe_heal=True)
                )

        return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
            action,
            campaign_id=campaign_id,
        )

    @staticmethod
    def ExpertCampaignAddRandomObligationFromExpertCampaignToHealHP(obligations: Sequence[str], *, campaign_id: str|None=None) -> 'Ability':
        from game.operate.worlds import Worlds
        from game.operate.campaign_logs import CampaignLog
        from game.card.factory import CardFactory
        from game.ability.factory import AbilityFactory
        from engine.lib import Random
        def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
            this = effect.this

            rest_obligations: Dict[Player, List[str]] = {}

            for player in Worlds.GetPlayers(effect):
                player_id = player.player_id
                card_ids = CampaignLog.GetListByPlayer("Obligations", player_id, effect)
                rest_obligations[player] = [x for x in obligations if x not in card_ids]
                if card_ids:
                    CardFactory.GenerateCards(card_ids, player.player_deck, effect.world)
                    player.player_deck.Shuffle(effect)

            for player in Worlds.GetPlayers(effect):
                def action(targets: Sequence['CardFace']):
                    card_id = Random.RandomChoice(rest_obligations[player])
                    CardFactory.GenerateCard(card_id, player.player_deck, effect.world)
                    this.HealthUnits(targets, "All", effect)
                    player.player_deck.Shuffle(effect)

                player.MayChooseOneAbility(
                    effect,
                    AbilityFactory.ForChoiceAbility(
                        "Add 1 random obligation from expert campaign set to their deck to heal their identity to its full hit point value",
                        action,
                        condition=rest_obligations[player] != []
                    ).SetTarget([player.GetIdentity()], canbe_heal=True)
                )

        return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
            action,
            campaign_id=campaign_id,
        )
