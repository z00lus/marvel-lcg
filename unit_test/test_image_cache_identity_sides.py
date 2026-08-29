import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from engine.file.cache import (
    CACHE_FOLDER,
    IMAGE_FOLDERS,
    IMAGE_SERVERS,
    TEXTURE_FOLDER,
    CEREBRO_REVERSED_IDENTITY_BASE_IDS,
    CEREBRO_SIDE_CACHE_REVISION,
    Cache,
)


class IdentitySideImageCacheTests(unittest.TestCase):

    def setUp(self):
        self.original_memory_cache = Cache.cache
        Cache.cache = {}

    def tearDown(self):
        Cache.cache = self.original_memory_cache

    def test_only_cerebro_reverses_known_identity_side_ids(self):
        cerebro = (
            "https://cerebrodatastorage.blob.core.windows.net/"
            "cerebro-cards/official/{card_id:U}.jpg"
        )
        marvelcdb = "https://marvelcdb.com/bundles/cards/{card_id}.png"

        affected_ids = (
            "16001",
            "16029",
            "32001",
            "32030",
            "33001",
            "34001",
            "35001",
            "36001",
            "37001",
            "38001",
        )
        for card_id in affected_ids:
            with self.subTest(card_id=card_id):
                self.assertEqual(
                    Cache._GetSourceCardId(cerebro, f"{card_id}a"),
                    f"{card_id}b",
                )
                self.assertEqual(
                    Cache._GetSourceCardId(cerebro, f"{card_id}b"),
                    f"{card_id}a",
                )

        self.assertEqual(Cache._GetSourceCardId(marvelcdb, "32030a"), "32030a")
        self.assertEqual(Cache._GetSourceCardId(cerebro, "40001a"), "40001a")

    def test_browser_revision_matches_the_server_cache_mapping(self):
        source_path = (
            Path(__file__).resolve().parents[1]
            / "public/js/card_image_url.ts"
        )
        source = source_path.read_text(encoding="utf-8")
        browser_base_ids = set(re.findall(r"'([0-9]{5})',\s*//", source))

        self.assertEqual(
            browser_base_ids,
            set(CEREBRO_REVERSED_IDENTITY_BASE_IDS),
        )
        self.assertIn(
            f"cerebroSideCacheRevision = '{CEREBRO_SIDE_CACHE_REVISION}'",
            source,
        )

    def test_revised_cache_key_ignores_an_existing_reversed_download(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cache_folder = root / "cache"
            cache_folder.mkdir()
            (cache_folder / "32030a.jpg").write_bytes(b"old reversed image")

            response = Mock()
            response.content = b"correct hero image"
            response.headers = {"Content-Type": "image/jpeg"}
            response.raise_for_status.return_value = None

            with patch.object(IMAGE_FOLDERS, "value", []), \
                patch.object(TEXTURE_FOLDER, "value", str(root / "textures")), \
                patch.object(CACHE_FOLDER, "value", str(cache_folder)), \
                patch.object(IMAGE_SERVERS, "value", [
                    "https://cerebrodatastorage.blob.core.windows.net/"
                    "cerebro-cards/official/{card_id:U}.jpg",
                ]), patch(
                    "engine.file.cache.requests.get",
                    return_value=response,
                ) as request, patch(
                    "engine.file.cache.ImageLib.TryRotateImage",
                    side_effect=lambda data: data,
                ):
                image = Cache.LoadImage("32030a")

            self.assertEqual(image, b"correct hero image")
            self.assertTrue(request.call_args.args[0].endswith("/32030B.jpg"))
            self.assertEqual(
                (cache_folder / "32030a.ronin-side-v1.jpg").read_bytes(),
                b"correct hero image",
            )

    def test_canonical_local_image_still_takes_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image_folder = root / "pics"
            cache_folder = root / "cache"
            image_folder.mkdir()
            cache_folder.mkdir()
            (image_folder / "32030a.jpg").write_bytes(b"local hero image")

            with patch.object(IMAGE_FOLDERS, "value", [str(image_folder)]), \
                patch.object(TEXTURE_FOLDER, "value", str(root / "textures")), \
                patch.object(CACHE_FOLDER, "value", str(cache_folder)), \
                patch.object(IMAGE_SERVERS, "value", [
                    "https://cerebrodatastorage.blob.core.windows.net/"
                    "cerebro-cards/official/{card_id:U}.jpg",
                ]), patch(
                    "engine.file.cache.requests.get",
                ) as request, patch(
                    "engine.file.cache.ImageLib.TryRotateImage",
                    side_effect=lambda data: data,
                ):
                image = Cache.LoadImage("32030a")

            self.assertEqual(image, b"local hero image")
            request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
