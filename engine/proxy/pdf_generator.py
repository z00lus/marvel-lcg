from collections import Counter
from dataclasses import dataclass
import io
import math
import os
import re
import uuid

from PIL import Image, ImageDraw, ImageOps

from engine.config import ConfigVariables
from engine.file import Cache, FileManager
from engine.lib import Json


PROXY_OUTPUT_FOLDER = ConfigVariables.Folder(
    'proxy_output_folder',
    './proxy-output/',
)


@dataclass(frozen=True)
class ProxyPdfResult:
    file_path: str
    display_path: str
    file_name: str
    card_faces: int
    pages: int


class ProxyPdfGenerator:
    """Build print-ready A4 proxy sheets from the installed game content.

    Each front/back face is rendered as a separate 63.5 x 88.9 mm tile. This
    keeps the output useful on ordinary simplex printers: two cut faces can be
    placed back-to-back in one opaque sleeve.
    """

    DPI = 300
    PAGE_WIDTH_MM = 210.0
    PAGE_HEIGHT_MM = 297.0
    CARD_WIDTH_MM = 63.5
    CARD_HEIGHT_MM = 88.9
    GAP_MM = 2.0
    COLUMNS = 3
    ROWS = 3
    CARDS_PER_PAGE = COLUMNS * ROWS
    MAX_CARD_FACES = 300
    ID_PATTERN = re.compile(r'^[A-Za-z0-9_.-]+$')

    HERO_CARD_KEYS = (
        'hero',
        'hero_deck',
        'player_deck',
        'set_aside',
        'obligations',
        'nemesis_set',
    )
    SCENARIO_CARD_KEYS = ('villain', 'schemes', 'set_aside', 'encounters')
    UNDERLING_CARD_KEYS = ('villain', 'expert_villain', 'set_aside', 'encounters')

    def __init__(self, output_folder: str|None=None) -> None:
        self.output_folder = output_folder or PROXY_OUTPUT_FOLDER.value

    @classmethod
    def ValidateId(cls, value: object, label: str) -> str:
        value = str(value or '').strip()
        if not value or not cls.ID_PATTERN.fullmatch(value):
            raise ValueError(f'Invalid {label}.')
        return value

    @staticmethod
    def _load_json(load_type: 'FileManager.JsonType', file_id: str) -> dict:
        file_path = FileManager.FindJsonPath(load_type, file_id)
        if not file_path:
            raise ValueError(f'Content "{file_id}" was not found.')
        data = Json.Load(file_path)
        if not isinstance(data, dict):
            raise ValueError(f'Content "{file_id}" is not a JSON object.')
        return data

    @staticmethod
    def _list_values(data: dict, *keys: str) -> list[str]:
        values: list[str] = []
        for key in keys:
            raw_values = data.get(key, [])
            if raw_values is None:
                continue
            if not isinstance(raw_values, list) or not all(
                    isinstance(value, str) for value in raw_values):
                raise ValueError(f'Invalid card list: {key}.')
            values.extend(raw_values)
        return values

    @staticmethod
    def _merge_variants(*variants: list[str]) -> list[str]:
        """Merge Standard/Expert variants without duplicating shared cards."""
        order: list[str] = []
        maximum_counts: Counter[str] = Counter()
        for variant in variants:
            variant_counts = Counter(variant)
            for card_id in variant:
                if card_id not in order:
                    order.append(card_id)
            for card_id, count in variant_counts.items():
                maximum_counts[card_id] = max(maximum_counts[card_id], count)

        result: list[str] = []
        for card_id in order:
            result.extend([card_id] * maximum_counts[card_id])
        return result

    @classmethod
    def _out_of_print_content_ids(cls) -> tuple[set[str], set[str]]:
        catalog = cls._load_json('SetInfo', 'sets_info.json')
        hero_ids: set[str] = set()
        scenario_ids: set[str] = set()
        for product in catalog.values():
            if not isinstance(product, dict) or product.get('out_of_print') is not True:
                continue
            hero_ids.update(cls._list_values(product, 'heroes'))
            scenario_ids.update(cls._list_values(product, 'scenarios'))
        return hero_ids, scenario_ids

    @staticmethod
    def _identity_face_id(hero: dict) -> str:
        hero_cards = ProxyPdfGenerator._list_values(hero, 'hero')
        if not hero_cards:
            return ''
        return hero_cards[0].split(',')[0].strip().lower()

    @classmethod
    def _is_out_of_print_hero_deck(cls, hero_id: str) -> bool:
        out_of_print_heroes, _ = cls._out_of_print_content_ids()
        if hero_id in out_of_print_heroes:
            return True

        # Synced MarvelCDB decks have their own numeric filename. Match them
        # to the physical Hero Pack by the identity card they contain.
        selected_identity = cls._identity_face_id(cls._load_json('Hero', hero_id))
        if not selected_identity:
            return False
        for out_of_print_hero in out_of_print_heroes:
            hero = cls._load_json('Hero', out_of_print_hero)
            if cls._identity_face_id(hero) == selected_identity:
                return True
        return False

    @classmethod
    def _require_out_of_print(cls, kind: str, content_id: str) -> None:
        if kind == 'hero':
            allowed = cls._is_out_of_print_hero_deck(content_id)
        elif kind == 'scenario':
            _, out_of_print_scenarios = cls._out_of_print_content_ids()
            allowed = content_id in out_of_print_scenarios
        else:
            raise ValueError('Proxy type must be "hero" or "scenario".')

        if not allowed:
            raise ValueError(
                'Proxy PDFs are available only for officially out-of-print '
                'heroes and scenarios.'
            )

    @staticmethod
    def _expand_faces(card_ids: list[str]) -> list[str]:
        faces: list[str] = []
        for card_id in card_ids:
            split_faces = [face.strip().lower() for face in card_id.split(',')]
            split_faces = [face for face in split_faces if face]
            if not split_faces:
                raise ValueError('A card has no printable face ID.')
            faces.extend(split_faces)
        return faces

    @classmethod
    def CollectHeroCards(cls, hero_id: str) -> tuple[str, list[str]]:
        hero_id = cls.ValidateId(hero_id, 'hero deck')
        hero = cls._load_json('Hero', hero_id)
        card_ids = cls._list_values(hero, *cls.HERO_CARD_KEYS)
        if not card_ids:
            raise ValueError('The selected hero deck contains no cards.')
        name = str(hero.get('deck_name') or hero.get('name') or hero_id).strip()
        return name, cls._expand_faces(card_ids)

    @classmethod
    def _collect_encounter_sets(cls, data: dict) -> list[str]:
        cards: list[str] = []
        set_names = cls._list_values(data, 'encounter_sets', 'modular_sets')
        for set_name in dict.fromkeys(set_names):
            encounter_set = cls._load_json('EncounterSet', set_name)
            cards.extend(cls._list_values(
                encounter_set,
                'villain',
                'expert_villain',
                'schemes',
                'set_aside',
                'encounters',
            ))
        return cards

    @classmethod
    def _scenario_variant_cards(
            cls,
            scenario: dict,
            *,
            include_villain: bool=True,
            ) -> list[str]:
        direct_keys = cls.SCENARIO_CARD_KEYS if include_villain else (
            'schemes', 'set_aside', 'encounters',
        )
        return [
            *cls._list_values(scenario, *direct_keys),
            *cls._collect_encounter_sets(scenario),
        ]

    @classmethod
    def _find_optional_scenario(cls, scenario_id: str) -> dict|None:
        # FindJsonPath logs a warning for an ordinary nullable miss. Listing the
        # configured scenario files avoids turning "no Expert variant" into a
        # server warning every time a proxy set is generated.
        from engine.file.manager import CUSTOM_SCENARIOS_FOLDER, SCENARIOS_FOLDERS

        expected_name = f'{scenario_id}.json'
        paths = FileManager.ListFiles(
            *SCENARIOS_FOLDERS.value,
            CUSTOM_SCENARIOS_FOLDER.value,
            ext='.json',
        )
        for file_path in paths:
            if FileManager.GetBaseName(file_path) == expected_name:
                data = Json.Load(file_path)
                if isinstance(data, dict):
                    return data
                raise ValueError(f'Content "{scenario_id}" is not a JSON object.')
        return None

    @classmethod
    def CollectScenarioCards(
            cls,
            scenario_id: str,
            underling_id: str|None=None,
            ) -> tuple[str, list[str]]:
        scenario_id = cls.ValidateId(scenario_id, 'scenario')
        scenario = cls._load_json('Campaign', scenario_id)
        expert = cls._find_optional_scenario(f'{scenario_id}_expert')

        underling_sets = cls._list_values(scenario, 'underling_sets')
        selected_underling: dict|None = None
        if underling_sets:
            underling_id = cls.ValidateId(underling_id, 'underling')
            if underling_id not in underling_sets:
                raise ValueError('The selected underling does not belong to this scenario.')
            selected_underling = cls._load_json('EncounterSet', underling_id)
        elif underling_id:
            raise ValueError('This scenario does not use an underling.')

        include_scenario_villain = selected_underling is None
        standard_cards = cls._scenario_variant_cards(
            scenario,
            include_villain=include_scenario_villain,
        )
        expert_cards = cls._scenario_variant_cards(
            expert,
            include_villain=include_scenario_villain,
        ) if expert else []
        cards = cls._merge_variants(standard_cards, expert_cards)

        if selected_underling:
            underling_villains = cls._merge_variants(
                cls._list_values(selected_underling, 'villain'),
                cls._list_values(selected_underling, 'expert_villain'),
            )
            cards.extend(underling_villains)
            cards.extend(cls._list_values(
                selected_underling,
                'set_aside',
                'encounters',
            ))

        if not cards:
            raise ValueError('The selected scenario contains no cards.')
        name = str(scenario.get('name') or scenario_id).strip()
        return name, cls._expand_faces(cards)

    @staticmethod
    def _slug(value: str) -> str:
        slug = value.lower().replace("'", '')
        slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
        return slug or 'proxy-set'

    @classmethod
    def _px(cls, millimetres: float) -> int:
        return round(millimetres * cls.DPI / 25.4)

    @classmethod
    def _render_page(cls, card_faces: list[str]) -> bytes:
        page_width = cls._px(cls.PAGE_WIDTH_MM)
        page_height = cls._px(cls.PAGE_HEIGHT_MM)
        card_width = cls._px(cls.CARD_WIDTH_MM)
        card_height = cls._px(cls.CARD_HEIGHT_MM)
        gap = cls._px(cls.GAP_MM)
        grid_width = cls.COLUMNS * card_width + (cls.COLUMNS - 1) * gap
        grid_height = cls.ROWS * card_height + (cls.ROWS - 1) * gap
        origin_x = (page_width - grid_width) // 2
        origin_y = (page_height - grid_height) // 2

        page = Image.new('RGB', (page_width, page_height), 'white')
        draw = ImageDraw.Draw(page)
        line_width = max(1, cls._px(0.18))

        for index, card_id in enumerate(card_faces):
            row, column = divmod(index, cls.COLUMNS)
            x = origin_x + column * (card_width + gap)
            y = origin_y + row * (card_height + gap)

            image_data = Cache.LoadImage(card_id)
            with Image.open(io.BytesIO(image_data)) as opened:
                card = ImageOps.exif_transpose(opened).convert('RGB')
                if card.width > card.height:
                    card = card.rotate(90, expand=True)
                card = ImageOps.fit(
                    card,
                    (card_width, card_height),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
                page.paste(card, (x, y))

            draw.rectangle(
                (x, y, x + card_width, y + card_height),
                outline='black',
                width=line_width,
            )

        output = io.BytesIO()
        page.save(output, format='JPEG', quality=94, subsampling=0, dpi=(cls.DPI, cls.DPI))
        page.close()
        return output.getvalue()

    @staticmethod
    def _write_object(file, offsets: list[int], object_id: int, value: bytes) -> None:
        offsets[object_id] = file.tell()
        file.write(f'{object_id} 0 obj\n'.encode('ascii'))
        file.write(value)
        file.write(b'\nendobj\n')

    @classmethod
    def _write_pdf(cls, card_faces: list[str], file_path: str) -> int:
        page_count = math.ceil(len(card_faces) / cls.CARDS_PER_PAGE)
        object_count = 2 + page_count * 3
        offsets = [0] * (object_count + 1)
        page_width_px = cls._px(cls.PAGE_WIDTH_MM)
        page_height_px = cls._px(cls.PAGE_HEIGHT_MM)
        page_width_points = cls.PAGE_WIDTH_MM * 72.0 / 25.4
        page_height_points = cls.PAGE_HEIGHT_MM * 72.0 / 25.4

        with open(file_path, 'wb') as file:
            file.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
            cls._write_object(file, offsets, 1, b'<< /Type /Catalog /Pages 2 0 R >>')

            page_ids = [3 + page_index * 3 for page_index in range(page_count)]
            children = ' '.join(f'{page_id} 0 R' for page_id in page_ids)
            pages = f'<< /Type /Pages /Count {page_count} /Kids [{children}] >>'
            cls._write_object(file, offsets, 2, pages.encode('ascii'))

            for page_index, page_id in enumerate(page_ids):
                image_id = page_id + 1
                content_id = page_id + 2
                page = (
                    f'<< /Type /Page /Parent 2 0 R '
                    f'/MediaBox [0 0 {page_width_points:.3f} {page_height_points:.3f}] '
                    f'/Resources << /XObject << /Im0 {image_id} 0 R >> >> '
                    f'/Contents {content_id} 0 R >>'
                )
                cls._write_object(file, offsets, page_id, page.encode('ascii'))

                start = page_index * cls.CARDS_PER_PAGE
                jpeg = cls._render_page(card_faces[start:start + cls.CARDS_PER_PAGE])
                image_header = (
                    f'<< /Type /XObject /Subtype /Image /Width {page_width_px} '
                    f'/Height {page_height_px} /ColorSpace /DeviceRGB '
                    f'/BitsPerComponent 8 /Filter /DCTDecode /Length {len(jpeg)} >>\nstream\n'
                ).encode('ascii')
                cls._write_object(
                    file,
                    offsets,
                    image_id,
                    image_header + jpeg + b'\nendstream',
                )

                commands = (
                    f'q\n{page_width_points:.3f} 0 0 {page_height_points:.3f} 0 0 cm\n'
                    f'/Im0 Do\nQ\n'
                ).encode('ascii')
                content = (
                    f'<< /Length {len(commands)} >>\nstream\n'.encode('ascii')
                    + commands
                    + b'endstream'
                )
                cls._write_object(file, offsets, content_id, content)

            xref_position = file.tell()
            file.write(f'xref\n0 {object_count + 1}\n'.encode('ascii'))
            file.write(b'0000000000 65535 f \n')
            for object_id in range(1, object_count + 1):
                file.write(f'{offsets[object_id]:010d} 00000 n \n'.encode('ascii'))
            trailer = (
                f'trailer\n<< /Size {object_count + 1} /Root 1 0 R >>\n'
                f'startxref\n{xref_position}\n%%EOF\n'
            )
            file.write(trailer.encode('ascii'))
        return page_count

    def Generate(
            self,
            kind: str,
            content_id: str,
            underling_id: str|None=None,
            ) -> ProxyPdfResult:
        content_id = self.ValidateId(content_id, kind or 'content')
        self._require_out_of_print(kind, content_id)
        if kind == 'hero':
            name, card_faces = self.CollectHeroCards(content_id)
        elif kind == 'scenario':
            name, card_faces = self.CollectScenarioCards(content_id, underling_id)
        else:
            raise ValueError('Proxy type must be "hero" or "scenario".')

        if len(card_faces) > self.MAX_CARD_FACES:
            raise ValueError('The selected proxy set is too large to generate safely.')

        FileManager.MakeDir(self.output_folder)
        name_slug = self._slug(name)
        id_slug = self._slug(content_id)
        output_slug = name_slug if name_slug == id_slug else f'{name_slug}-{id_slug}'
        file_name = f'{output_slug}-{kind}-proxy.pdf'
        file_path = FileManager.JoinPath(self.output_folder, file_name)
        temporary_path = f'{file_path}.{uuid.uuid4().hex}.tmp'
        try:
            pages = self._write_pdf(card_faces, temporary_path)
            FileManager.Replace(temporary_path, file_path)
        finally:
            if FileManager.Exists(temporary_path):
                FileManager.Delete(temporary_path)

        display_folder = self.output_folder.rstrip('/\\')
        if not os.path.isabs(display_folder) and not display_folder.startswith('.'):
            display_folder = f'./{display_folder}'
        display_path = f'{display_folder}/{file_name}'
        return ProxyPdfResult(
            file_path=file_path,
            display_path=display_path,
            file_name=file_name,
            card_faces=len(card_faces),
            pages=pages,
        )
