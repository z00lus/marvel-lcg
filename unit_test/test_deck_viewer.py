import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401
from cards.database import CardsDB
from cards.paper import Paper
from engine.device.web.server.server_get import GameServerGet


class TestDeckViewerCardMetadata(unittest.IsolatedAsyncioTestCase):

    async def test_card_paper_is_returned_as_json(self) -> None:
        paper = Paper(
            card_id='16012',
            pic_id='',
            type='Ally',
            is_unique=True,
            name='Starhawk',
            desc={'Cost': '2', 'Class': 'Protection'},
            traits=['AERIAL', 'GUARDIAN'],
            pack='gmw',
        )
        request = SimpleNamespace(
            rel_url=SimpleNamespace(query_string='16012'),
        )

        with patch.object(CardsDB, 'FindCardPaper', return_value=paper):
            response = await GameServerGet.get_card_json(
                object.__new__(GameServerGet),
                request,
            )

        self.assertEqual(response.content_type, 'application/json')
        payload = json.loads(response.text)
        self.assertEqual(payload['card_id'], '16012')
        self.assertEqual(payload['name'], 'Starhawk')
        self.assertEqual(payload['pack'], 'gmw')
        self.assertEqual(payload['desc']['Class'], 'Protection')


if __name__ == '__main__':
    unittest.main()
