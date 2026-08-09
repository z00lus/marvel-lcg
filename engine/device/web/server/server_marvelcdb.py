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

    def __init__(self) -> None:
        super().__init__()
        self.AddAwaitGetSecurity(
            '/marvelcdb_sync_status',
            self.marvelcdb_sync_status,
        )
        self.AddPostSecurity('/sync_marvelcdb_decks', self.sync_marvelcdb_decks)
