from core import *
import io
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

    width = 127*2
    height = 176*2

    clean = re.compile('<.*?>')
    font_size = 18
    font: ImageFont.ImageFont|ImageFont.FreeTypeFont

    ################################################################################
    #
    @staticmethod
    def Initialize() -> None:
        try:
            ImageCreatorHelper.font = ImageFont.truetype(FONT.value, ImageCreatorHelper.font_size)
        except IOError:
            ImageCreatorHelper.font = ImageFont.load_default()

    @staticmethod
    def CreateImageColor(color: Tuple[int, int, int]) -> bytes:
        # Create a new white image with the specified dimensions
        width, height = ImageCreatorHelper.width, ImageCreatorHelper.height
        image = Image.new("RGB", (width, height), color)
        return ImageLib.ImageToByteArray(image)

    @staticmethod
    def CreateImage(image_data: bytes|None, name: str, type: str="", desc: str="", aspect: str="", rotate: bool=False) -> bytes:
        def remove_html_tags(text: str):
            return ImageCreatorHelper.re.sub(ImageCreatorHelper.clean, '', text)

        if image_data:
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
        else:

            if aspect not in ImageCreator.aspect_dict:
                color = "white"
            else:
                color = ImageCreator.aspect_dict[aspect]

            width, height = ImageCreatorHelper.width, ImageCreatorHelper.height
            image = Image.new("RGB", (width, height), color)
            if rotate:
                image = image.rotate(-90, expand=True)
                width, height = height, width

        # Create a draw object
        draw = ImageDraw.Draw(image)

        ImageCreatorHelper.DrawText(draw, name, (10, 4), ImageCreatorHelper.font, width)
        ImageCreatorHelper.DrawText(draw, type, (4, ImageCreatorHelper.font_size + 4), ImageCreatorHelper.font, width)

        padding = 10
        max_width = width - padding * 2
        start_height = int(height * .2)
        if isinstance(ImageCreatorHelper.font, ImageFont.FreeTypeFont):
            ImageCreatorHelper.DrawText(draw, remove_html_tags(desc), (padding, start_height), ImageCreatorHelper.font, max_width)

        if rotate:
            image = image.rotate(90, expand=True)

        # Convert the white image with text to bytes and return
        return ImageLib.ImageToByteArray(image)

    @staticmethod
    def DrawText(draw: ImageDraw.ImageDraw, text: str, position: Tuple[int, int], font: ImageFont.ImageFont|ImageFont.FreeTypeFont, max_width: int, fill: str='black', wrap: bool=False) -> None:
        lines: List[str] = []
        filtered_text = text
        words = filtered_text.split()
        current_line = ""

        # for word in words:
        #     # Check if adding the next word would exceed the max width
        #     test_line = f"{current_line} {word}".strip()
        #     if draw.textsize(test_line, font=ImageCreatorHelper.font)[0] <= max_width:
        #         current_line = test_line
        #     else:
        #         lines.append(current_line)
        #         current_line = word

        # Add the last line if there's any text left
        if current_line:
            lines.append(current_line)

        # Adjust the starting position to center the text vertically
        y_position = position[1]

        # Draw each line of text on the image
        for line in lines:
            draw.text((position[0], y_position), line, fill=fill, font=font) # type: ignore
            y_position += ImageCreatorHelper.font_size + 1

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
        type: str
        text: str
        aspect: str
        rotate: bool

    @staticmethod
    def GetCardRenderData(card_id: str) -> 'RenderData':
        from cards.database import CardsDB
        from engine.lib import TransText

        name = ""
        type = ""
        text = ""
        aspect = ""
        rotate = False
        if card_id in CardsDB.papers:
            text = CardsDB.papers[card_id].text
            name = CardsDB.papers[card_id].name
            type = CardsDB.papers[card_id].type
            translate_text = TransText(card_id)
            if translate_text.is_translated:
                text = translate_text.text_symbol
            if type in ["SideScheme", "MainScheme", "PlayerSideScheme", "Status"]:
                rotate = True
            if "Class" in CardsDB.papers[card_id].desc:
                aspect = CardsDB.papers[card_id].desc["Class"]

        return ImageCreator.RenderData(card_id, name, type, text, aspect, rotate)

    ################################################################################
    #
    @staticmethod
    def CreateNoImage(card_id: str) -> bytes:
        if card_id in ImageCreator.face_back_dict:
            return ImageCreator.LoadImageByColor(card_id)

        data = ImageCreator.GetCardRenderData(card_id)
        if not ImageCreator.show_image_text:
            return ImageCreator.LoadImageByColor(data.aspect)

        image_data = ImageCreatorHelper.CreateImage(None, data.name, data.type, data.text, data.aspect, data.rotate)
        return image_data
