from aiohttp import web

from engine.device.web.server.server_base import GameServerBase
from engine.deck_editor import DeckEditor
from engine.file.manager import STARTER_DECK_FOLDER, USER_DECK_FOLDER
from engine.task import TaskManager


class GameServerDeckEditor(GameServerBase):
    async def deck_editor(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object.')
        except Exception:
            return web.json_response({'error': 'Expected a JSON object.'}, status=400)
        editor = DeckEditor(STARTER_DECK_FOLDER.value, USER_DECK_FOLDER.value)
        args = [data.get('source'), data.get('id')]
        action = data.get('action')
        if action == 'load':
            method = editor.load
        elif action in ('validate', 'save'):
            method = editor.check if action == 'validate' else editor.save
            args += [data.get('player_deck'), data.get('aspects')]
            if action == 'save':
                args += [data.get('name'), data.get('revision')]
        else:
            return web.json_response({'error': 'Unknown deck editor action.'}, status=400)
        try:
            result = await TaskManager.ToThread(method, *args)
            return web.json_response(result, headers=self.HeaderNoStore)
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400, headers=self.HeaderNoStore)
        except OSError:
            return web.json_response(
                {'error': 'Could not save the deck. Check free disk space and deck folder permissions.'},
                status=500, headers=self.HeaderNoStore,
            )

    def __init__(self):
        super().__init__()
        self.AddPostSecurity('/deck_editor', self.deck_editor)
