from aiohttp import web

from engine.device.web.server.server_base import GameServerBase
from engine.log import Log
from engine.task import TaskManager


class GameServerGameHistory(GameServerBase):

    async def _history_json_body(self, request: web.Request) -> dict:
        try:
            data = await request.json()
        except Exception as exc:
            raise ValueError('Expected a JSON request.') from exc
        if not isinstance(data, dict):
            raise ValueError('Expected a JSON object.')
        return data

    async def _run_history(self, method, *args) -> web.Response:
        try:
            result = await TaskManager.ToThread(method, *args)
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400)
        except Exception as exc:
            Log.FailedTrace('WEB', exc, no_take_as_error=True)
            return web.json_response(
                {'error': 'Game history could not be updated.'},
                status=500,
            )
        return web.json_response(result)

    def _history(self):
        history = self.game.game_history
        if history is None or not history.available:
            raise RuntimeError('Game history is unavailable.')
        return history

    async def save_physical_game(self, request: web.Request) -> web.Response:
        try:
            data = await self._history_json_body(request)
            history = self._history()
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400)
        except RuntimeError as exc:
            return web.json_response({'error': str(exc)}, status=503)
        return await self._run_history(history.SavePhysicalGame, data)

    async def delete_physical_game(self, request: web.Request) -> web.Response:
        try:
            data = await self._history_json_body(request)
            history = self._history()
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400)
        except RuntimeError as exc:
            return web.json_response({'error': str(exc)}, status=503)
        return await self._run_history(history.DeletePhysicalGame, data.get('id'))

    async def save_collection(self, request: web.Request) -> web.Response:
        try:
            data = await self._history_json_body(request)
            history = self._history()
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400)
        except RuntimeError as exc:
            return web.json_response({'error': str(exc)}, status=503)
        return await self._run_history(history.SaveCollection, data.get('owned_products'))

    def __init__(self) -> None:
        super().__init__()
        self.AddPostSecurity('/physical_games/save', self.save_physical_game)
        self.AddPostSecurity('/physical_games/delete', self.delete_physical_game)
        self.AddPostSecurity('/collection/save', self.save_collection)
