from core import *
from engine.device.web.server.server_base import GameServerBase

CATEGORY_NAME = "WEB"

class GameServerHTML(GameServerBase):

    @override
    def __init__(self) -> None:
        super().__init__()

        self.AddHtmlSecurity('/main', './public/main.html')
        self.AddHtmlSecurity('/deck', './public/deck.html')
        self.AddHtmlSecurity('/cards', './public/cards.html')
        self.AddHtmlSecurity('/solo', './public/solo.html')
        self.AddHtmlSecurity('/campaign', './public/campaign.html')
        self.AddHtmlSecurity('/scene', './public/scene.html')
        self.AddHtmlSecurity('/replay', './public/replay.html')
        self.AddHtmlSecurity('/settings', './public/settings.html')
        self.AddHtmlSecurity('/statistics', './public/statistics.html')
        self.AddHtmlSecurity('/proxy', './public/proxy.html')
        self.AddHtmlSecurity('/puzzle', './public/replay.html')
        self.AddHtmlSecurity('/credits', './public/credits.html')
        self.AddHtmlSecurity('/puzzle_editor', './public/puzzle_editor.html')
        self.AddHtmlSecurity('/puzzle_test', './public/replay.html')
        self.AddHtmlSecurity('/report', './public/report.html')
        self.AddHtmlSecurity(
            '/ronin-start-background.webp',
            './assets/textures/ronin-start-background.webp',
        )
