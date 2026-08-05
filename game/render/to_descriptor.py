from itertools import chain
from core import *
from game.card import *
from game.card.face import *
from game.render.descriptor.world import WorldDescriptor
from game.render.descriptor.card import CardDescriptor
from game.deck import *
from game.world import *
from game.player import *

def deck_to_descriptors(deck: 'Deck') -> List['CardDescriptor']:
    return list(chain.from_iterable(
        ToDescriptor.Card(face.card) for face in deck.GetAll()
    ))

class ToDescriptor:

    @staticmethod
    def Player(player: 'Player') -> 'WorldDescriptor.PlayerDescriptor':
        player_descriptor = WorldDescriptor.PlayerDescriptor()

        player_descriptor.area_hero                 = deck_to_descriptors(player.area_hero)
        player_descriptor.allies                    = deck_to_descriptors(player.allies)
        player_descriptor.supports                  = deck_to_descriptors(player.supports)
        player_descriptor.player_deck               = deck_to_descriptors(player.player_deck)
        player_descriptor.player_discard_pile       = deck_to_descriptors(player.discard_pile)
        player_descriptor.dealt_encounter_cards     = deck_to_descriptors(player.dealt_encounter_cards)
        player_descriptor.hand_cards                = deck_to_descriptors(player.hand_cards)
        player_descriptor.engaged_enemies           = deck_to_descriptors(player.engaged_minions)
        player_descriptor.set_aside_nemesis_sets    = deck_to_descriptors(player.set_aside_nemesis_sets)
        player_descriptor.additional_deck           = deck_to_descriptors(player.additional_deck)
        player_descriptor.additional_discard_pile   = deck_to_descriptors(player.additional_discard_pile)
        for name, deck in player.special_decks.items():
            player_descriptor.special_decks[name] = deck_to_descriptors(deck)
        player_descriptor.obligations_area          = deck_to_descriptors(player.obligations_area)
        player_descriptor.environment_area          = deck_to_descriptors(player.area_environment)
            
        player_descriptor.resources = player.res_pool.Get().text_legacy
        player_descriptor.is_eliminated = player.is_eliminated
        return player_descriptor

    @staticmethod
    def World(world: 'World', event_name: str, sound_name: str) -> 'WorldDescriptor':
        world_descriptor = WorldDescriptor()

        world_descriptor.render_id = world.render.last_render_id
        world_descriptor.round_id = world.round_id

        world_descriptor.phase = world.GetPhaseText()
        world_descriptor.event_name = event_name

        world_descriptor.prompt_last_text = world.render.last_prompt
        world_descriptor.prompt = world.render.prompt
        world_descriptor.max_card_object_id = len(world.object_manager.card_dict)
        world_descriptor.sound_name = sound_name

        world_descriptor.active_card_ids = world.render.last_active_card_ids

        world_descriptor.players = []
        for player in world.const_seat_order_players:
            world_descriptor.players.append(ToDescriptor.Player(player))

        scenario = world.GetScenario()

        world_descriptor.area_villain           = deck_to_descriptors(scenario.area_villain)
        world_descriptor.villain_deck           = deck_to_descriptors(scenario.villain_deck)
        world_descriptor.encounter_deck         = deck_to_descriptors(scenario.encounter_deck)
        world_descriptor.encounter_discard_pile = deck_to_descriptors(scenario.encounter_discard_pile)
        world_descriptor.area_schemes_main      = deck_to_descriptors(world.area_schemes_main)
        world_descriptor.main_schemes_deck      = deck_to_descriptors(world.main_schemes_deck)
        world_descriptor.area_schemes_side      = deck_to_descriptors(world.area_schemes_side)

        world_descriptor.area_boost             = deck_to_descriptors(world.area_boosting)
        world_descriptor.area_environment       = deck_to_descriptors(world.area_environment)
        world_descriptor.area_evidence          = deck_to_descriptors(world.area_evidence)
        world_descriptor.area_rule              = deck_to_descriptors(world.area_rule)
        world_descriptor.area_mission           = deck_to_descriptors(world.area_mission)

        world_descriptor.area_processing = []
        for player in world.const_seat_order_players:
            world_descriptor.area_processing.extend(deck_to_descriptors(player.area_processing))
        world_descriptor.area_processing.extend(deck_to_descriptors(world.area_processing))
        world_descriptor.area_revealing         = deck_to_descriptors(world.area_revealing)

        world_descriptor.area_removed           = deck_to_descriptors(world.area_removed)
        world_descriptor.area_insert            = deck_to_descriptors(world.area_insert)
        world_descriptor.area_set_aside         = deck_to_descriptors(world.aside_deck)
        world_descriptor.area_set_aside         += deck_to_descriptors(world.aside_modular)
        world_descriptor.victory_display        = deck_to_descriptors(world.victory_display)
        world_descriptor.area_status_cards      = deck_to_descriptors(world.area_status_cards)

        for deck in world.additional_decks:
            faces = deck_to_descriptors(deck)
            world_descriptor.additional_decks.append(faces)
        for deck in world.additional_discard_piles:
            faces = deck_to_descriptors(deck)
            world_descriptor.additional_discard_piles.append(faces)

        world_descriptor.area_resources = []
        for player in world.const_seat_order_players:
            world_descriptor.area_resources.extend(deck_to_descriptors(player.area_resources))

        return world_descriptor

    @staticmethod
    def Card(card: 'Card') -> List['CardDescriptor']:

        card_descriptor = [card.Render()]

        for face in card.components.status.GetDeck().GetAll():
            card_descriptor += ToDescriptor.Card(face.card)
        for face in card.components.inventory.GetDeck().GetAll():
            card_descriptor += ToDescriptor.Card(face.card)
        for face in card.components.placed_card.GetDeck().GetAll():
            card_descriptor += ToDescriptor.Card(face.card)
        for face in card.components.boostable.GetDeck().GetAll():
            card_descriptor += ToDescriptor.Card(face.card)
        return card_descriptor
