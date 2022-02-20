from __future__ import annotations

import discord

from io import BytesIO
from PIL import Image, ImageFont, ImageSequence
from pilmoji import Pilmoji

from bot.helpers import wrap_text
from bot.helpers.misc import proportionally_scale, to_thread
from bot.helpers.transparency import save_transparent_gif

__all__ = 'IFunnyCaption',


class IFunnyCaption:
    """Asynchrounous IFunny caption renderer.

    This is meant to be used in a context manager.
    """

    MAX_CHARS = 360
    MIN_WIDTH = 200
    MAX_WIDTH = 600
    LINE_SPACING = 2.5

    def __init__(self, image_bytes: bytes, *, text: str) -> None:
        self._image_bytes: bytes = image_bytes
        self._rescale: tuple[int, int] = None
        self._fallback_duration: int = None

        self.text: str = text[:self.MAX_CHARS]
        self.font: ImageFont.FreeTypeFont = None
        self.image: Image.Image = None

        self.caption_image: Image.Image = None
        self.frames: list[Image.Image] = []
        self.durations: list[int] = []

    @property
    def font_size(self) -> int:
        return self.font.size

    @property
    def offset(self) -> int:
        return self.caption_image.height

    @property
    def width(self) -> int:
        if self._rescale:
            return self._rescale[0]
        return self.image.width

    @property
    def height(self) -> int:
        if self._rescale:
            return self._rescale[1]
        return self.image.height

    @property
    def size(self) -> tuple[int, int]:
        return self._rescale or self.image.size

    @property
    def final_size(self) -> tuple[int, int]:
        return self.width, self.height + self.offset

    @to_thread
    def _open_image(self) -> None:
        self.image = image = Image.open(BytesIO(self._image_bytes))
        self._fallback_duration = image.info.get('duration', 64)

        self._rescale = proportionally_scale(
            image.size,
            min_dimension=self.MIN_WIDTH,
            max_dimension=self.MAX_WIDTH
        )

    @to_thread
    def _open_font(self) -> None:
        self.font = ImageFont.truetype(
            './bot/assets/fonts/futura.ttf',
            size=self.width // (
                9 if self.width < 400 else 12
            )
        )

    @to_thread
    def _close_image(self) -> None:
        self.image.close()
        self.caption_image.close()

        for frame in self.frames:
            frame.close()

        self.frames = []

    def _split_text(self) -> list[str]:
        return wrap_text(self.text, self.font, self.width)

    def _render_caption(self) -> None:
        lines = self._split_text()
        line_count = len(lines)

        padding = round(self.font_size / 2.3)

        height = self.font_size * line_count
        height += round((line_count - 1) * self.LINE_SPACING)  # Line spacing
        height += padding * 2

        image = self.caption_image = Image.new('RGBA', (self.width, height), (255, 255, 255))

        with Pilmoji(image, emoji_position_offset=(0, 4)) as pilmoji:
            for i, line in enumerate(lines):
                offset = int(self.LINE_SPACING * i + self.font_size * i)

                width, _ = pilmoji.getsize(line, self.font)
                x_offset = int((self.width - width) / 2)

                pilmoji.text((x_offset, padding // 2 + offset), line, (0, 0, 0), self.font)

    def _render_frame(self, frame: Image.Image, /) -> None:
        actual = Image.new("RGBA", self.final_size)

        frame = frame.convert('RGBA')
        actual.paste(self.caption_image, (0, 0))
        actual.paste(frame, (0, self.offset), frame)

        self.frames.append(actual)
        self.durations.append(frame.info.get('duration', self._fallback_duration))

        frame.close()
        del frame

    @to_thread
    def _render(self) -> tuple[BytesIO, str]:
        self._render_caption()

        for frame in ImageSequence.Iterator(self.image):
            if self._rescale:
                frame = frame.resize(self._rescale)
            self._render_frame(frame)

        stream = BytesIO()

        if len(self.durations) > 1:
            save_transparent_gif(self.frames, self.durations, stream)
            stream.seek(0)
            return stream, 'gif'

        self.frames[0].save(stream, 'png')
        stream.seek(0)
        return stream, 'png'

    async def render(self) -> discord.File:
        stream, fmt = await self._render()
        return discord.File(stream, f'caption.{fmt}')

    async def __aenter__(self) -> IFunnyCaption:
        await self._open_image()
        await self._open_font()
        return self

    async def __aexit__(self, *_) -> None:
        await self._close_image()
        del self.font
