from urllib.parse import quote

from aiohttp import web

from engine.device.web.server.server_base import GameServerBase
from engine.log import Log
from engine.task import TaskManager
from engine.proxy import ProxyPdfGenerator


class GameServerProxy(GameServerBase):

    async def generate_proxy_pdf(self, request: web.Request) -> web.StreamResponse:
        try:
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object.')

            result = await TaskManager.ToThread(
                self.proxy_pdf_generator.Generate,
                str(data.get('kind', '')).strip(),
                str(data.get('id', '')).strip(),
                str(data.get('underling_id', '')).strip() or None,
            )
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400)
        except Exception as exc:
            Log.FailedTrace('WEB', exc, no_take_as_error=True)
            return web.json_response(
                {'error': 'The proxy PDF could not be generated.'},
                status=500,
            )

        headers = {
            'Content-Disposition': (
                f"attachment; filename*=UTF-8''{quote(result.file_name)}"
            ),
            'Cache-Control': 'no-store',
            'X-Proxy-Path': result.display_path,
            'X-Proxy-Cards': str(result.card_faces),
            'X-Proxy-Pages': str(result.pages),
        }
        return web.FileResponse(
            result.file_path,
            headers=headers,
        )

    def __init__(self) -> None:
        super().__init__()
        self.proxy_pdf_generator = ProxyPdfGenerator()
        self.AddPostSecurity('/proxy/generate', self.generate_proxy_pdf)
