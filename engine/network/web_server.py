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
import os
import re

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


class AssetVersion:
    """Content-derived token that versions the URLs of static code.

    Every css/js reference in a served page is rewritten to
    ``/v/<token>/public/...``, and those URLs are then safe to cache as
    ``immutable``: the URL itself changes whenever the code does, so a returning
    browser cannot serve a stale copy of a file that has since been edited.

    Two decisions worth stating, because the obvious alternatives do not work
    here:

    **A path prefix, not a query string.** The pages load ES modules, and a
    relative import resolves against the *path* of the importing module -- a
    query string is not inherited. From ``/public/js/solo.js?v=2``, the
    ``./marvelcdb_deck.js`` import still resolves to the unversioned
    ``/public/js/marvelcdb_deck.js`` and keeps its stale cached copy, so
    query-string versioning covers the entry point and silently misses the
    dependency graph. A prefix is inherited, so one rewrite in the HTML versions
    every module reachable from it.

    **Derived from content, not from Ver.ui_version_str.** The engine already
    forces a clean-cache interstitial when that string changes
    (``IsVersionMatch``); the stale-asset problem still happened, because the
    release that changed the code did not bump the string. A token keyed on it
    would not have busted anything. Hashing the bytes removes the dependency on
    remembering to bump.
    """

    URL_PREFIX = '/v'
    FOLDERS = ('./public/js', './public/css')
    TOKEN_LENGTH = 12

    # Matches only what Compute() can emit, so a real file living under a path
    # that happens to start with /v/ is not mistaken for a versioned URL.
    _PREFIX_PATTERN = re.compile(r'^/v/([0-9a-f]{%d})(?=/)' % TOKEN_LENGTH)

    # Local css/js in an href/src. Anything absolute (http:, //) or of another
    # type is left alone: media is content-addressed already and genuinely
    # immutable, so it does not need or want a token.
    _REFERENCE_PATTERN = re.compile(
        r'''(?P<attr>\b(?:href|src)\s*=\s*)(?P<quote>["'])(?P<url>/(?!/)[^"']*?\.(?:css|js))(?P<query>\?[^"']*)?(?P=quote)''',
        re.IGNORECASE,
    )

    _token: str|None = None

    @classmethod
    def Token(cls) -> str:
        """The current token, computed once per process."""
        if cls._token is None:
            cls._token = cls.Compute()
        return cls._token

    @classmethod
    def Compute(cls) -> str:
        digest = hashlib.sha256()
        for folder in cls.FOLDERS:
            for directory, _sub_folders, file_names in sorted(os.walk(folder)):
                for file_name in sorted(file_names):
                    file_path = os.path.join(directory, file_name)
                    # The path is hashed as well as the bytes, so that renaming
                    # or removing a file changes the token even when the
                    # surviving contents are unchanged.
                    digest.update(os.path.relpath(file_path, folder).encode('utf-8'))
                    try:
                        with open(file_path, 'rb') as file:
                            digest.update(file.read())
                    except OSError as exc:
                        # An unreadable file must not take the server down, but
                        # it must still perturb the token: silently hashing
                        # nothing would let a broken deploy look cached-correct.
                        Log.Debug(CATEGORY_NAME, f'asset hash skipped {file_path}: {exc}')
                        digest.update(b'<unreadable>')
        return digest.hexdigest()[:cls.TOKEN_LENGTH]

    @classmethod
    def Reset(cls) -> None:
        """Drop the memoised token. For tests, and for a future reload hook."""
        cls._token = None

    @classmethod
    def StripPrefix(cls, path: str) -> Tuple[str, bool]:
        """Return ``(path_without_prefix, was_versioned)``.

        Any well-formed token is accepted rather than only the current one, so a
        page cached from an earlier build still resolves to the file that exists
        now instead of 404ing. ``ReadFile`` only marks the current token as
        immutable; bytes returned through an older token are never cached.
        """
        match = cls._PREFIX_PATTERN.match(path)
        if not match:
            return path, False
        return path[match.end():], True

    @classmethod
    def HasCurrentPrefix(cls, path: str) -> bool:
        match = cls._PREFIX_PATTERN.match(path)
        return bool(match and match.group(1) == cls.Token())

    @classmethod
    def RewriteHtml(cls, html: str) -> str:
        prefix = f'{cls.URL_PREFIX}/{cls.Token()}'

        def replace(match: 're.Match[str]') -> str:
            url = match.group('url')
            if cls.StripPrefix(url)[1]:
                return match.group(0)
            quote = match.group('quote')
            query = match.group('query') or ''
            return f'{match.group("attr")}{quote}{prefix}{url}{query}{quote}'

        return cls._REFERENCE_PATTERN.sub(replace, html)


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
        # A versioned URL names one exact build of one file, so it can be
        # cached without revalidation. `immutable` tells the browser to skip the
        # conditional request it would otherwise make on a forced reload.
        WebServer.HeaderCacheImmutable = {
            'Cache-Control': f'public, max-age={CACHE_MAX_AGE.value}, immutable'
        }
        # A 404 is not a fact about the world, it is a fact about right now:
        # caching it for a year meant a file added or fixed later stayed missing
        # until the browser cache was cleared by hand.
        WebServer.HeaderNoStore = {'Cache-Control': 'no-store'}

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
                return self.ReadHtmlFile(html)
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
    def ReadHtmlFile(self, file_path: str, find_paths: List[str]=[]) -> web.Response:
        """Serve a page with its css/js references versioned.

        The page itself must not be cached, or the browser keeps serving an old
        document containing old tokens and the versioning never takes effect.
        """
        response = self.ReadFile(file_path, find_paths)
        if response.status != 200 or not response.body:
            # Leave a 404 with the no-store ReadFile gave it. Overwriting that
            # with `no-cache` would still be an improvement on a year, but it
            # permits storing the response, and it is the weaker guarantee.
            return response

        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        try:
            html = bytes(response.body).decode('utf-8')
        except UnicodeDecodeError:
            return response

        response.body = AssetVersion.RewriteHtml(html).encode('utf-8')
        return response

    @final
    def ReadFile(self, file_path: str, find_paths: List[str]=[]) -> web.Response:
        has_current_version = AssetVersion.HasCurrentPrefix(file_path)
        file_path, is_versioned = AssetVersion.StripPrefix(file_path)

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
                return web.Response(status=404, headers=self.HeaderNoStore)
            data = read_file(found_path, True)
            mime_type = MimeType.GetMimeType(file_path)
            if has_current_version:
                header = self.HeaderCacheImmutable
            elif is_versioned:
                # Serving current bytes through an old content URL keeps an
                # already-open page alive, but caching that response as
                # immutable would permanently associate the wrong bytes with
                # the old token.
                header = self.HeaderNoStore
            elif Build.release:
                header = self.HeaderCache
            else:
                header = {}
            return web.Response(body=data, content_type=mime_type, headers=header)
        except Exception as exc:
            Log.Debug(CATEGORY_NAME, f"{file_path=}")
            Log.FailedTrace(CATEGORY_NAME, exc)
            return web.Response(status=404, headers=self.HeaderNoStore)

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
            return self.ReadHtmlFile(request.path, ['./public/'])

        async def handle_css(request: web.Request):
            return self.ReadFile(request.path, ['./public/css', './public/'])

        async def handle_js(request: web.Request):
            return self.ReadFile(request.path, ['./public/js', './public/'])

        async def handle_ts(request: web.Request):
            if Build.release:
                return web.Response(status=404, headers=self.HeaderNoStore)
            else:
                return self.ReadFile(request.path, ['./public/js', './public/'])

        async def handle_js_map(request: web.Request):
            if Build.release:
                return web.Response(status=404, headers=self.HeaderNoStore)
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
