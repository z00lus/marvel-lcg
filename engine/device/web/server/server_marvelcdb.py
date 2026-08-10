from aiohttp import web

from engine.device.web.server.server_base import GameServerBase
from engine.task import TaskManager


class GameServerMarvelCdb(GameServerBase):

    async def marvelcdb_sync_status(self, request: web.Request) -> web.Response:
        status = await TaskManager.ToThread(
            self.device_manager.marvelcdb_deck_sync.GetStatus,
        )
        return web.json_response(status)

    async def sync_marvelcdb_decks(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({'error': 'Expected a JSON request.'}, status=400)

        deck_ids = data.get('deck_ids', '')
        try:
            result = await TaskManager.ToThread(
                self.device_manager.marvelcdb_deck_sync.SyncDecks,
                deck_ids,
            )
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400)
        except Exception as exc:
            return web.json_response(
                {'error': f'MarvelCDB synchronization failed: {exc}'},
                status=500,
            )
        return web.json_response(result)

    async def _json_body(self, request: web.Request) -> dict:
        try:
            data = await request.json()
        except Exception:
            raise ValueError('Expected a JSON request.')
        if not isinstance(data, dict):
            raise ValueError('Expected a JSON object.')
        return data

    async def _run(self, method, *args) -> web.Response:
        try:
            result = await TaskManager.ToThread(method, *args)
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400)
        except Exception as exc:
            return web.json_response(
                {'error': f'MarvelCDB request failed: {exc}'},
                status=500,
            )
        return web.json_response(result)

    async def resolve_marvelcdb_deck(self, request: web.Request) -> web.Response:
        """Convert a pasted MarvelCDB link or ID into a playable deck.

        Nothing is written to disk -- the caller passes the result straight to
        `/new` as `hero_json`.
        """
        try:
            data = await self._json_body(request)
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400)

        return await self._run(
            self.device_manager.marvelcdb_deck_sync.ResolveDeck,
            data.get('deck', ''),
        )

    async def save_campaign_deck(self, request: web.Request) -> web.Response:
        """Freeze a resolved deck against a campaign run."""
        try:
            data = await self._json_body(request)
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400)

        campaign_id = str(data.get('campaign_id', '')).strip()
        deck = data.get('deck')
        if not campaign_id:
            return web.json_response({'error': 'A campaign is required.'}, status=400)
        if not isinstance(deck, dict):
            return web.json_response({'error': 'A resolved deck is required.'}, status=400)

        return await self._run(
            self.device_manager.marvelcdb_deck_sync.SaveCampaignDeck,
            campaign_id,
            deck,
        )

    async def refresh_campaign_deck(self, request: web.Request) -> web.Response:
        """Re-pull a frozen campaign deck, only when the player asks."""
        try:
            data = await self._json_body(request)
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400)

        hero_id = str(data.get('hero_id', '')).strip()
        if not hero_id:
            return web.json_response({'error': 'A campaign deck is required.'}, status=400)

        return await self._run(
            self.device_manager.marvelcdb_deck_sync.RefreshCampaignDeck,
            hero_id,
        )

    def __init__(self) -> None:
        super().__init__()
        self.AddAwaitGetSecurity(
            '/marvelcdb_sync_status',
            self.marvelcdb_sync_status,
        )
        self.AddPostSecurity('/sync_marvelcdb_decks', self.sync_marvelcdb_decks)
        self.AddPostSecurity('/resolve_marvelcdb_deck', self.resolve_marvelcdb_deck)
        self.AddPostSecurity('/save_campaign_deck', self.save_campaign_deck)
        self.AddPostSecurity('/refresh_campaign_deck', self.refresh_campaign_deck)
