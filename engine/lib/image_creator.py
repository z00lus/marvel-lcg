from core import *
import io
import html
from PIL import Image, ImageFont, ImageDraw, ImageOps
from engine.config import ConfigVariables

SHOW_IMAGE_TEXT = ConfigVariables.Bool('show_image_text', False)
FONT = ConfigVariables.Str('font', 'cour.ttf')

class ImageLib:

    @staticmethod
    def GetContentType(image_data: bytes) -> str:
        if image_data.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        if image_data.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        if len(image_data) >= 12 and image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP':
            return 'image/webp'
        if image_data.startswith((b'GIF87a', b'GIF89a')):
            return 'image/gif'
        return 'application/octet-stream'

    @staticmethod
    def ImageToByteArray(image: Image.Image) -> bytes:
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        bytes_io = io.BytesIO()
        image.save(bytes_io, format='jpeg')  # You can change the format if needed
        return bytes_io.getvalue()

    @staticmethod
    def TryRotateImage(image_data: bytes) -> bytes:
        img_io: Image.Image = Image.open(io.BytesIO(image_data))
        # 1. Normalize orientation based on EXIF tags (what the browser does)
        # This physically rotates pixels so 'top-left' is actually top-left.
        img_io = ImageOps.exif_transpose(img_io)
        width, height = img_io.size
        if width > height:
            img_io = img_io.rotate(90, expand=True)
            image_data = ImageLib.ImageToByteArray(img_io)
        return image_data

class ImageCreatorHelper:
    import re

    # Keep the physical Marvel Champions card ratio while rendering enough
    # pixels for the rules text to remain readable in the browser preview.
    width = 596
    height = 834

    clean = re.compile('<.*?>')
    font_size = 25
    font: ImageFont.ImageFont|ImageFont.FreeTypeFont

    ################################################################################
    #
    @staticmethod
    def Initialize() -> None:
        ImageCreatorHelper.font = ImageCreatorHelper.LoadFont(ImageCreatorHelper.font_size)

    @staticmethod
    def LoadFont(size: int, *, bold: bool=False) -> ImageFont.ImageFont|ImageFont.FreeTypeFont:
        candidates = [
            FONT.value,
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf" if bold else
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for candidate in candidates:
            try:
                return ImageFont.truetype(candidate, size)
            except IOError:
                continue
        return ImageFont.load_default()

    @staticmethod
    def CreateImageColor(color: Tuple[int, int, int]) -> bytes:
        # Create a new white image with the specified dimensions
        width, height = ImageCreatorHelper.width, ImageCreatorHelper.height
        image = Image.new("RGB", (width, height), color)
        return ImageLib.ImageToByteArray(image)

    @staticmethod
    def CleanRulesText(text: str) -> str:
        text = ImageCreatorHelper.re.sub(r"<(br|hr)\s*/?>", "\n", text, flags=ImageCreatorHelper.re.IGNORECASE)
        text = ImageCreatorHelper.re.sub(ImageCreatorHelper.clean, '', text)
        text = html.unescape(text)
        replacements = {
            "[star]": "*", "[energy]": "ENERGY", "[mental]": "MENTAL",
            "[physical]": "PHYSICAL", "[wild]": "WILD", "[per_hero]": "/ player",
            "[acceleration]": "ACCELERATION", "[[": "", "]]": "",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        return text.strip()

    @staticmethod
    def TypeLabel(card_type: str) -> str:
        return ImageCreatorHelper.re.sub(r"(?<!^)(?=[A-Z])", " ", card_type).upper()

    @staticmethod
    def CreateImage(image_data: bytes|None,
                    name: str,
                    type: str="",
                    desc: str="",
                    aspect: str="",
                    rotate: bool=False,
                    *,
                    subtitle: str="",
                    attributes: Dict[str, str]|None=None,
                    traits: Sequence[str]=(),
                    card_id: str="",
                    ) -> bytes:

        if image_data:
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
        else:

            width, height = ImageCreatorHelper.width, ImageCreatorHelper.height
            image = Image.new("RGB", (width, height), (12, 19, 28))
            if rotate:
                image = image.rotate(-90, expand=True)
                width, height = height, width

        # Create a draw object
        draw = ImageDraw.Draw(image)

        if image_data is None:
            accent = ImageCreator.aspect_dict.get(aspect, ImageCreator.aspect_dict[""])
            accent_dark = tuple(max(0, value - 75) for value in accent)
            border = max(8, int(min(width, height) * .018))
            radius = max(18, int(min(width, height) * .035))
            draw.rounded_rectangle(
                (border, border, width-border-1, height-border-1),
                radius=radius,
                fill=(16, 25, 36),
                outline=accent,
                width=max(4, border//2),
            )

            header_height = int(height * .17)
            draw.rounded_rectangle(
                (border*2, border*2, width-border*2, header_height),
                radius=radius//2,
                fill=accent_dark,
                outline=(225, 229, 226),
                width=2,
            )

            title_font = ImageCreatorHelper.LoadFont(max(25, int(min(width, height) * .055)), bold=True)
            subtitle_font = ImageCreatorHelper.LoadFont(max(17, int(min(width, height) * .029)))
            small_bold = ImageCreatorHelper.LoadFont(max(16, int(min(width, height) * .027)), bold=True)
            body_font = ImageCreatorHelper.LoadFont(max(19, int(min(width, height) * .034)))

            left = border * 3
            title_right = width - border * 3
            attributes = attributes or {}
            cost = attributes.get("Cost")
            if cost is not None:
                badge = int(min(width, height) * .105)
                title_right -= badge + border
                draw.ellipse(
                    (width-left-badge, left, width-left, left+badge),
                    fill=(245, 245, 238), outline=accent, width=4,
                )
                cost_font = ImageCreatorHelper.LoadFont(max(25, badge//2), bold=True)
                cost_box = draw.textbbox((0, 0), cost, font=cost_font)
                draw.text(
                    (width-left-badge/2-(cost_box[2]-cost_box[0])/2,
                     left+badge/2-(cost_box[3]-cost_box[1])/2-2),
                    cost, fill=(15, 18, 22), font=cost_font,
                )

            title = name or "Missing card art"
            ImageCreatorHelper.DrawText(
                draw, title, (left, left), title_font, title_right-left,
                fill="white", wrap=True, max_lines=2,
            )
            if subtitle:
                draw.text((left, header_height-int(height*.044)), subtitle, fill=(220, 224, 226), font=subtitle_font)

            type_y = header_height + border
            type_label = ImageCreatorHelper.TypeLabel(type or "CARD")
            draw.text((left, type_y), type_label, fill=accent, font=small_bold)

            stats = []
            for key in ("REC", "THW", "ATK", "DEF", "SCH", "HP", "HS", "StartingThreat", "Boost"):
                value = attributes.get(key)
                if value is not None:
                    label = {"StartingThreat": "THREAT"}.get(key, key.upper())
                    stats.append(f"{label} {value}")
            stats_y = type_y + int(height*.045)
            if stats:
                draw.text((left, stats_y), "   ".join(stats), fill=(245, 245, 238), font=small_bold)

            traits_y = stats_y + (int(height*.045) if stats else 0)
            if traits:
                draw.text((left, traits_y), " • ".join(traits), fill=(205, 211, 215), font=subtitle_font)

            panel_top = max(int(height*.34), traits_y + int(height*.055))
            panel_bottom = height - int(height*.105)
            draw.rounded_rectangle(
                (left-border, panel_top, width-left+border, panel_bottom),
                radius=radius//2,
                fill=(242, 239, 226),
                outline=accent,
                width=3,
            )
            rules = ImageCreatorHelper.CleanRulesText(desc)
            ImageCreatorHelper.DrawText(
                draw, rules or "Card text unavailable.",
                (left, panel_top+border*2), body_font,
                width-left*2, fill=(24, 26, 29), wrap=True,
                max_height=panel_bottom-panel_top-border*4,
            )

            resource = attributes.get("RES", "")
            resource_names = {
                "Y": "ENERGY", "B": "MENTAL", "R": "PHYSICAL", "W": "WILD",
            }
            resource_symbols = " / ".join(resource_names.get(value, value) for value in resource)
            footer_y = height - int(height*.075)
            if resource_symbols:
                draw.text((left, footer_y), resource_symbols, fill=accent, font=small_bold)
            footer = "TEXT-ONLY CARD"
            if card_id:
                footer += f"  •  {card_id.upper()}"
            footer_box = draw.textbbox((0, 0), footer, font=subtitle_font)
            draw.text((width-left-(footer_box[2]-footer_box[0]), footer_y), footer, fill=(172, 180, 185), font=subtitle_font)

        if rotate:
            image = image.rotate(90, expand=True)

        # Convert the white image with text to bytes and return
        return ImageLib.ImageToByteArray(image)

    @staticmethod
    def DrawText(draw: ImageDraw.ImageDraw,
                 text: str,
                 position: Tuple[int, int],
                 font: ImageFont.ImageFont|ImageFont.FreeTypeFont,
                 max_width: int,
                 fill: str='black',
                 wrap: bool=False,
                 *,
                 max_height: int|None=None,
                 max_lines: int|None=None,
                 ) -> int:
        paragraphs = text.splitlines() or [text]
        lines: List[str] = []
        for paragraph in paragraphs:
            words = paragraph.split()
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if not wrap or draw.textbbox((0, 0), test_line, font=font)[2] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            elif paragraph == "":
                lines.append("")

        was_truncated = False
        if max_lines is not None:
            was_truncated = len(lines) > max_lines
            lines = lines[:max_lines]

        sample_box = draw.textbbox((0, 0), "Ag", font=font)
        line_height = max(1, sample_box[3] - sample_box[1] + 7)
        if max_height is not None:
            line_limit = max(1, max_height // line_height)
            was_truncated = was_truncated or len(lines) > line_limit
            lines = lines[:line_limit]

        if was_truncated and lines:
            lines[-1] = lines[-1].rstrip(". ") + "…"

        y_position = position[1]
        for line in lines:
            draw.text((position[0], y_position), line, fill=fill, font=font) # type: ignore
            y_position += line_height
        return y_position

class ImageCreator:
    cache_images: Dict[str, bytes] = {}

    show_image_text: bool

    face_back_dict: Dict[str, Tuple[int, int, int]] = {
        'player':       (14 , 78 , 139),
        'encounter':    (230, 125, 34 ),
        'villain':      (132, 41 , 110),
        'no_image':     (51 , 51 , 51 ),
    }

    aspect_dict: Dict[str, Tuple[int, int, int]] = {
        "":             (135, 147, 159),
        "Aggression":   (237, 51 , 51 ),
        "Justice":      (217, 202, 51 ),
        "Leadership":   (93 , 156, 191),
        "Protection":   (84 , 255, 149),
        "'Pool":        (200, 102, 153),
        "Basic":        (171, 164, 153),
        "Encounter":    (170, 154, 139),
        "Hero":         (188, 176, 164)
    }

    @staticmethod
    def Initialize() -> None:
        ImageCreatorHelper.Initialize()
        ImageCreator.show_image_text = SHOW_IMAGE_TEXT.value
        ImageCreator.cache_images["white"] = ImageCreatorHelper.CreateImage(None, "No Image")

    @staticmethod
    def LoadImageByColor(color: str) -> bytes:
        if color not in ImageCreator.cache_images:
            if color in ImageCreator.face_back_dict:
                image = ImageCreatorHelper.CreateImageColor(ImageCreator.face_back_dict[color])
            elif color in ImageCreator.aspect_dict:
                image = ImageCreatorHelper.CreateImageColor(ImageCreator.aspect_dict[color])
            else:
                image = ImageCreator.cache_images["white"]
            ImageCreator.cache_images[color] = image
        return ImageCreator.cache_images[color]

    ################################################################################
    #
    @dataclass
    class RenderData:
        card_id: str
        name: str
        subtitle: str
        type: str
        text: str
        aspect: str
        rotate: bool
        attributes: Dict[str, str]
        traits: Sequence[str]

    @staticmethod
    def GetCardRenderData(card_id: str) -> 'RenderData':
        from cards.database import CardsDB
        from engine.lib import TransText

        name = ""
        subtitle = ""
        type = ""
        text = ""
        aspect = ""
        rotate = False
        attributes: Dict[str, str] = {}
        traits: Sequence[str] = []
        if card_id in CardsDB.papers:
            paper = CardsDB.papers[card_id]
            text = paper.text
            name = paper.name
            subtitle = paper.subtitle
            type = paper.type
            attributes = dict(paper.desc)
            traits = list(paper.traits)
            translate_text = TransText(card_id)
            if translate_text.is_translated:
                text = translate_text.text_symbol
            if type in ["SideScheme", "MainScheme", "PlayerSideScheme", "Status"]:
                rotate = True
            if "Class" in paper.desc:
                aspect = paper.desc["Class"]
            elif type in ["Obligation", "Minion", "Villain", "SideScheme", "Treachery", "Attachment", "Environment"]:
                aspect = "Encounter"

        return ImageCreator.RenderData(card_id, name, subtitle, type, text, aspect, rotate, attributes, traits)

    ################################################################################
    #
    @staticmethod
    def CreateNoImage(card_id: str) -> bytes:
        if card_id in ImageCreator.face_back_dict:
            return ImageCreator.LoadImageByColor(card_id)

        data = ImageCreator.GetCardRenderData(card_id)
        if not data.name and not ImageCreator.show_image_text:
            return ImageCreator.LoadImageByColor(data.aspect)

        image_data = ImageCreatorHelper.CreateImage(
            None,
            data.name,
            data.type,
            data.text,
            data.aspect,
            data.rotate,
            subtitle=data.subtitle,
            attributes=data.attributes,
            traits=data.traits,
            card_id=data.card_id,
        )
        return image_data
