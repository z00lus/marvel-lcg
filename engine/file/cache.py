from core import *
import requests
from engine.lib import ImageCreator, ImageLib
from engine.log import Log
from engine.file import FileManager
from engine.config import ConfigVariables

CATEGORY_NAME = "CACHE"

IMAGE_FOLDERS   = ConfigVariables.Folders('image_folders', ["./assets/pics/"])
TEXTURE_FOLDER  = ConfigVariables.Folder('texture_folder', "./assets/textures/")
CACHE_FOLDER    = ConfigVariables.Folder('cache_folder', "./assets/cache/")
IMAGE_SERVERS   = ConfigVariables.ListStr('image_servers', [])
BREAK_WHEN_LOAD_ONLINE_IMAGE = ConfigVariables.Bool('break_when_load_online_image', False)

STATUS_TEXTURES = frozenset({"tough", "stunned", "confused"})

# Cerebro names these identity sides after their printed A/B faces, while the
# engine and MarvelCDB consistently use "a" for hero and "b" for alter-ego.
# Keep this source-specific: local images and every other image server already
# use the engine's card ids.
CEREBRO_REVERSED_IDENTITY_BASE_IDS = frozenset({
    "16001",  # Groot
    "16029",  # Rocket Raccoon
    "32001",  # Colossus
    "32030",  # Shadowcat
    "33001",  # Cyclops
    "34001",  # Phoenix
    "35001",  # Wolverine
    "36001",  # Storm
    "37001",  # Gambit
    "38001",  # Rogue
})

CEREBRO_SIDE_CACHE_REVISION = "ronin-side-v1"

class Cache:

    cache: Dict[str, bytes] = {}
    link_pic: Dict[str, str] = {}

    @staticmethod
    def SetLinkPic(card_id: str, link_to_pic_id: str):
        Cache.link_pic[card_id] = link_to_pic_id

    @staticmethod
    def SetCache(card_id: str, data: bytes):
        Cache.cache[card_id] = data

    @staticmethod
    def _GetSourceCardId(site: str, card_id: str) -> str:
        if "cerebrodatastorage.blob.core.windows.net" not in site.lower():
            return card_id
        if len(card_id) != 6 or card_id[:-1] not in CEREBRO_REVERSED_IDENTITY_BASE_IDS:
            return card_id
        if card_id[-1] == "a":
            return f"{card_id[:-1]}b"
        if card_id[-1] == "b":
            return f"{card_id[:-1]}a"
        return card_id

    @staticmethod
    def _GetPersistentCacheName(card_id: str) -> str:
        if len(card_id) == 6 and card_id[:-1] in CEREBRO_REVERSED_IDENTITY_BASE_IDS:
            return f"{card_id}.{CEREBRO_SIDE_CACHE_REVISION}"
        return card_id

    @staticmethod
    def LoadImage(card_id: str) -> bytes:
        # if url in ['enthralled_minion', 'minion', 'ultron_facedown_drone']:
        #     url = 'player'
        card_id = card_id.lstrip("/")

        if card_id in Cache.cache:
            return Cache.cache[card_id]

        assert card_id != "", f"{card_id=}"
        file_name = card_id

        local_folders = IMAGE_FOLDERS.value + [TEXTURE_FOLDER.value]
        persistent_cache_name = Cache._GetPersistentCacheName(file_name)

        def try_load_image_data(image_data: bytes):
            # Status artwork is already authored in its final landscape
            # orientation. Keep its PNG bytes intact; the browser rotates it
            # clockwise inside the portrait status-card frame.
            if file_name in STATUS_TEXTURES:
                return image_data
            return ImageLib.TryRotateImage(image_data)

        # Load the image from the cache and images
        def try_load_image_path(file_path: str) -> bytes|None:
            if file_name in STATUS_TEXTURES:
                extensions = [".png", ".webp", ".jpg"]
            else:
                extensions = [".webp", ".jpg", ".png"]
            for ext_name in extensions:
                check_path = file_path + ext_name
                if FileManager.Exists(check_path):
                    with FileManager.OpenFile(check_path, read=True, bin=True) as file:
                        return try_load_image_data(file.Read())
            return None

        def try_load_image_name(name: str, folders: Sequence[str]) -> bytes|None:
            for cache_folder in folders:
                file_paths: List[str] = []
                file_paths.append(f"{cache_folder}/{name}")
                for file_path in file_paths:
                    image_data = try_load_image_path(file_path)
                    if image_data:
                        return image_data
            return None

        # User-provided images use the engine's canonical ids and always win.
        image_data = try_load_image_name(file_name, local_folders)
        if not image_data:
            # A revised key deliberately bypasses pre-fix Cerebro files that
            # may already be present under the old canonical cache name.
            image_data = try_load_image_name(
                persistent_cache_name,
                [CACHE_FOLDER.value],
            )
        if image_data:
            Cache.SetCache(file_name, image_data)
            return image_data

        if file_name in Cache.link_pic:
            image_data = Cache.LoadImage(Cache.link_pic[file_name])
            if image_data:
                return image_data

        def check_is_card_id(s: str):
            import re
            # Pattern to match: four digits followed by a lowercase letter
            pattern = r'^\d{5}[a-z]?$'
            return re.match(pattern, s)

        def save_to_file(file_name: str, ext_name: str, data: bytes):
            file_path = FileManager.JoinPath(CACHE_FOLDER.value, f"{file_name}.{ext_name}")
            FileManager.MakeDir(FileManager.GetDirName(file_path))
            with FileManager.OpenFile(file_path, write=True, bin=True) as file:
                file.Write(data)

        if IMAGE_SERVERS.value and check_is_card_id(card_id):
            # Load the image from the internet
            skip_break = not BREAK_WHEN_LOAD_ONLINE_IMAGE.value
            if not skip_break:
                Debug.DebugBreak()

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }

            # "https://cerebrodatastorage.blob.core.windows.net/cerebro-cards/official/${card_id}.jpg",
            # "https://marvelcdb.com/bundles/cards/${card_id}.jpg",
            # "https://marvelcdb.com/bundles/cards/${card_id}.png",

            for site in IMAGE_SERVERS.value:
                source_card_id = Cache._GetSourceCardId(site, card_id)
                full_url = site
                full_url = full_url.replace('{card_id}', source_card_id)
                full_url = full_url.replace('{card_id:U}', source_card_id.upper())

                try:
                    Log.DebugInfo(CATEGORY_NAME, f"Downloading from {full_url}")

                    response = requests.get(full_url, headers=headers, timeout=3)
                    response.raise_for_status()

                    content_type = response.headers.get('Content-Type')

                    ext_name = "bmp"
                    if content_type:
                        # Determine the image format based on the Content-Type
                        if 'image/jpeg' in content_type:
                            ext_name = "jpg"
                        elif 'image/png' in content_type:
                            ext_name = "png"
                        elif 'image/webp' in content_type:
                            ext_name = "webp"

                    # Check if the response is successful
                    Log.DebugInfo(CATEGORY_NAME, f"Downloaded: {file_name}")
                    data = response.content
                    # Save the image to the cache
                    save_to_file(persistent_cache_name, ext_name, data)
                    # Get the image data from the response
                    image_data = try_load_image_data(data)
                    Cache.SetCache(file_name, image_data)
                    return image_data
                except requests.exceptions.Timeout:
                    Log.Warn(CATEGORY_NAME, f"Timeout occurred while downloading {file_name}")
                except requests.exceptions.RequestException as e:
                    Log.Warn(CATEGORY_NAME, f"Request failed with error: {e}")

        # raise Exception(f"Failed to load {file_name} from the internet")
        image_data = ImageCreator.CreateNoImage(card_id)
        Cache.SetCache(file_name, image_data)
        return image_data
