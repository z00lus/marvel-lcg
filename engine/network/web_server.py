from typing import TypeAlias
from core import *
from aiohttp import web
from build import Build
from engine.config import ConfigVariables
from engine.task import TaskManager
# from engine.job import JobManager
from engine.lib import MimeType, Json, Ver
from engine.log import Log
from engine.file import FileManager
import hashlib
import asyncio

CATEGORY_NAME = "WEB"

SOUND_FOLDERS   = ConfigVariables.Folders('sound_folders', ["./assets/sounds/"])
IMAGE_FOLDERS   = ConfigVariables.Folders('image_folders')
TEXTURE_FOLDER  = ConfigVariables.Folder('texture_folder')
CACHE_MAX_AGE   = ConfigVariables.Int('cache_max_age', 31536000)
"""
one hour:   3600
one day:    86400
one week:   604800
one year:   31536000
"""

PASSWORD            = ConfigVariables.Str('password', "")
DETECTED_VERSION    = ConfigVariables.Bool('detected_version', True)

class WebServer:

    HandleAsyncType: TypeAlias = Callable[["web.Request"], Awaitable["web.StreamResponse"]]
    HandleNonAsyncType: TypeAlias = Callable[["web.Request"], "web.StreamResponse"]

    def __init__(self) -> None:
        self.web_app = web.Application()
        self.runner = web.AppRunner(self.web_app)

        if PASSWORD.value:
            self.hash_password = hashlib.md5(PASSWORD.value.encode()).hexdigest()
        else:
            self.hash_password = None

        WebServer.HeaderCache = {'Cache-Control': f'public, max-age={CACHE_MAX_AGE.value}'}

    ################################################################################
    #
    @final
    def LoadHtmlAuthenticate(self):
        return self.ReadFile('./public/authenticate.html')

    @final
    def LoadHtmlCleanCache(self):
        return self.ReadFile('./public/clean_cache.html')

    ################################################################################
    #
    @final
    def AddNonAwaitGetSecurity(self, path: str, handle: HandleNonAsyncType):
        async def new_handle(request: web.Request) -> web.StreamResponse:
            if not self.IsAuthenticate(request):
                return self.LoadHtmlAuthenticate()
            elif not self.IsVersionMatch(request):
                return self.LoadHtmlCleanCache()
            else:
                return await TaskManager.ToThread(handle, request)
        self.web_app.router.add_get(path, new_handle)

    @final
    def AddAwaitGetSecurity(self, path: str, handle: HandleAsyncType, need_auth: bool=True, need_check_version: bool=True):
        async def new_handle(request: web.Request) -> web.StreamResponse:
            if need_auth and not self.IsAuthenticate(request):
                return self.LoadHtmlAuthenticate()
            elif need_check_version and not self.IsVersionMatch(request):
                return self.LoadHtmlCleanCache()
            else:
                return await handle(request)
        self.web_app.router.add_get(path, new_handle)

    @final
    def IsAuthenticate(self, request: web.Request) -> bool:
        if not self.hash_password:
            return True
        app_password_cookie = request.cookies.get('session_token')
        if app_password_cookie != self.hash_password:
            return False
        return True

    @final
    def IsVersionMatch(self, request: web.Request) -> bool:
        if not DETECTED_VERSION.value:
            return True
        app_version_cookie = request.cookies.get('app_version')
        if app_version_cookie and app_version_cookie != Ver.ui_version_str:
            return False
        elif not app_version_cookie:
            return False
        return True

    @final
    def AddHtmlSecurity(self, path: str, html: str):
        async def handle(request: web.Request) -> web.StreamResponse:
            if not self.IsAuthenticate(request):
                return self.LoadHtmlAuthenticate()
            elif not self.IsVersionMatch(request):
                return self.LoadHtmlCleanCache()
            else:
                response = self.ReadFile(html)
                response.headers['Cache-Control'] = 'no-cache, must-revalidate'
                return response
        self.web_app.router.add_get(path, handle)

    @final
    def AddPost(self, path: str, handle: HandleAsyncType):
        self.web_app.router.add_post(path, handle)

    @final
    def AddPostSecurity(self, path: str, handle: HandleAsyncType):
        async def new_handle(request: web.Request) -> web.StreamResponse:
            if not self.IsAuthenticate(request):
                return web.Response(status=401)
            else:
                return await handle(request)
        self.web_app.router.add_post(path, new_handle)

    @final
    def ReadJsonFile(self, file_path: str|None, *, do_cache: bool=True) -> web.Response:
        if file_path:
            data = Json.Load(file_path)
            compressed_data = Json.DumpGZip(data)
            headers = {'Content-Encoding': 'gzip'}

            if do_cache:
                headers.update(self.HeaderCache)

            return web.Response(body=compressed_data, content_type='application/json', headers=headers)
        else:
            return web.json_response({})

    @final
    def ReadFile(self, file_path: str, find_paths: List[str]=[]) -> web.Response:
        if file_path.startswith("/"):
            file_path = "." + file_path

        def find_path(file_path: str) -> str|None:
            for path in ["./"] + find_paths:
                check_path = FileManager.JoinPath(path, file_path)
                if FileManager.Exists(check_path):
                    return check_path
            return None

        def read_file(path: str, bin: bool):
            try:
                with FileManager.OpenFile(path, read=True, bin=bin) as file:
                    data = file.Read()
                    if not bin:
                        data = data.encode('utf-8')
                return data
            except Exception as exc:
                Log.FailedTrace(CATEGORY_NAME, exc)
                return ""

        try:
            found_path = find_path(file_path)
            if found_path is None:
                Log.Debug(CATEGORY_NAME, f"File not found: {file_path}")
                return web.Response(status=404, headers=self.HeaderCache)
            data = read_file(found_path, True)
            mime_type = MimeType.GetMimeType(file_path)
            if Build.release:
                header = self.HeaderCache
            else:
                header = {}
            return web.Response(body=data, content_type=mime_type, headers=header)
        except Exception as exc:
            Log.Debug(CATEGORY_NAME, f"{file_path=}")
            Log.FailedTrace(CATEGORY_NAME, exc)
            return web.Response(status=404, headers=self.HeaderCache)

    @final
    def Run(self, ip: str, port: int, name: str="") -> None:
        async def start_server() -> None:
            try:
                await self.runner.setup()
                site = web.TCPSite(self.runner, ip, port)
                await site.start()
                Log.Print(f"{name}:\thttp://{ip}:{port}")
            except Exception as exc:
                Log.Print(f"{name}:\thttp://{ip}:{port} failed")
                Log.FailedTrace(CATEGORY_NAME, exc, no_take_as_error=True)

        self.ip = ip
        self.port = port
        self.server_task = TaskManager.AddTask(start_server, name="WebServer", run_forever=True)

    def Shutdown(self) -> None:
        if hasattr(self, 'server_task') and self.server_task.loop.is_running():
            cleanup = asyncio.run_coroutine_threadsafe(self.runner.cleanup(), self.server_task.loop)
            try:
                cleanup.result(timeout=5)
            except Exception as exc:
                Log.FailedTrace(CATEGORY_NAME, exc, no_take_as_error=True)

    ################################################################################
    #
    def AddDefaultGet(self):
        from build import Build

        async def handle_favicon(request: web.Request):
            file_path = './public/favicon.ico'
            response = self.ReadFile(file_path)
            response.headers['Cache-Control'] = 'no-cache, must-revalidate'
            return response

        async def handle_authenticate(request: web.Request) -> web.Response:
            data = await request.json()
            password_attempt = data.get('password')
            session_token = hashlib.md5(password_attempt.encode()).hexdigest()

            response = web.Response()
            response.set_cookie(
                'session_token',
                session_token,
                max_age=31536000, # 1 year
                path='/',
                httponly=True, # VERY IMPORTANT: Prevents JavaScript access to the cookie
                # secure=True, # IMPORTANT: Use this flag ONLY if serving over HTTPS
                # samesite='Lax' # Recommended: 'Lax' or 'Strict'
            )
            return response

        async def handle_get_version(request: web.Request) -> web.Response:
            # response = web.Response(text=Ver.ui_version_str)
            # Hack, make browser treat it as images and store in cache
            response = web.Response(body=Ver.ui_version_str, content_type='image/jpeg', headers=self.HeaderCache)
            response.set_cookie(
                'app_version',
                Ver.ui_version_str,
                max_age=365 * 24 * 60 * 60, # 1 year
                path='/',
                httponly=False
            )
            return response

        async def handle_html(request: web.Request):
            return self.ReadFile(request.path, ['./public/'])

        async def handle_css(request: web.Request):
            return self.ReadFile(request.path, ['./public/css', './public/'])

        async def handle_js(request: web.Request):
            return self.ReadFile(request.path, ['./public/js', './public/'])

        async def handle_ts(request: web.Request):
            if Build.release:
                return web.Response(status=404, headers=self.HeaderCache)
            else:
                return self.ReadFile(request.path, ['./public/js', './public/'])

        async def handle_js_map(request: web.Request):
            if Build.release:
                return web.Response(status=404, headers=self.HeaderCache)
            else:
                return self.ReadFile(request.path, ['./public/js', './public/'])

        def handle_mp3(request: web.Request):
            return self.ReadFile(request.path, SOUND_FOLDERS.value)

        def handle_wav(request: web.Request):
            return self.ReadFile(request.path, SOUND_FOLDERS.value)

        async def handle_font(request: web.Request):
            file_path = request.path
            file_path = file_path.split("/")[-1]
            return self.ReadFile(file_path, ['./public/fonts'])

        async def handle_svg(request: web.Request):
            file_path = request.path
            file_path = file_path.split("/")[-1]
            return self.ReadFile(file_path, [TEXTURE_FOLDER.value])

        async def handle_gif(request: web.Request):
            return self.ReadFile('sparkles.gif', IMAGE_FOLDERS.value + [TEXTURE_FOLDER.value])

        self.AddAwaitGetSecurity('/favicon.ico', handle_favicon)

        self.AddPost(r'/authenticate', handle_authenticate)
        self.AddAwaitGetSecurity(r'/get_version', handle_get_version, need_auth=False, need_check_version=False)

        self.AddAwaitGetSecurity(r'/{path:.+\.html}', handle_html)
        self.AddAwaitGetSecurity(r'/{path:.+\.css}', handle_css)
        self.AddAwaitGetSecurity(r'/{path:.+\.js}', handle_js)
        self.AddAwaitGetSecurity(r'/{path:.+\.ts}', handle_ts)
        self.AddAwaitGetSecurity(r'/{path:.+\.js.map}', handle_js_map)

        self.AddNonAwaitGetSecurity(r'/{path:.+\.mp3}', handle_mp3)
        self.AddNonAwaitGetSecurity(r'/{path:.+\.wav}', handle_wav)

        self.AddAwaitGetSecurity(r'/{path:.+\.eot}', handle_font)
        self.AddAwaitGetSecurity(r'/{path:.+\.woff}', handle_font)
        self.AddAwaitGetSecurity(r'/{path:.+\.ttf}', handle_font)

        self.AddAwaitGetSecurity(r'/{path:.+\.svg}', handle_svg)
        self.AddAwaitGetSecurity(r'/{path:.+\.gif}', handle_gif)
