from aiohttp import web

from engine.device.web.server.server_base import GameServerBase
from engine.log import Log
from engine.task import TaskManager
from game.game_run.campaign_progress import CampaignProgressConflict


class GameServerCampaignProgress(GameServerBase):

    async def campaign_progress(self, request: web.Request) -> web.Response:
        record = await TaskManager.ToThread(self.game.campaign_progress.Load)
        return web.json_response({
            'campaign': record['campaign'] if record else None,
        })

    async def migrate_campaign_progress(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object.')
            record, migrated = await TaskManager.ToThread(
                self.game.campaign_progress.Migrate,
                data,
            )
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400)
        except Exception as exc:
            Log.FailedTrace('WEB', exc, no_take_as_error=True)
            return web.json_response(
                {'error': 'Campaign progress could not be migrated.'},
                status=500,
            )
        return web.json_response({
            'campaign': record['campaign'],
            'migrated': migrated,
        })

    async def advance_campaign_progress(self, request: web.Request) -> web.Response:
        try:
            result = await TaskManager.ToThread(
                self.game.campaign_progress.AdvanceGame,
                self.game,
            )
        except CampaignProgressConflict as exc:
            return web.json_response({'error': str(exc)}, status=409)
        except Exception as exc:
            Log.FailedTrace('WEB', exc, no_take_as_error=True)
            return web.json_response(
                {'error': 'Campaign progress could not be updated.'},
                status=500,
            )
        return web.json_response(result)

    def __init__(self) -> None:
        super().__init__()
        self.AddAwaitGetSecurity('/campaign_progress', self.campaign_progress)
        self.AddPostSecurity(
            '/campaign_progress/migrate',
            self.migrate_campaign_progress,
        )
        self.AddPostSecurity(
            '/campaign_progress/advance',
            self.advance_campaign_progress,
        )
