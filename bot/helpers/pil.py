from __future__ import annotations

import re
from functools import partial
from typing import Callable, Iterator, TYPE_CHECKING

from fontTools.ttLib import TTFont
from pilmoji import EMOJI_REGEX, Node, NodeType, getsize

if TYPE_CHECKING:
    from PIL.ImageDraw import Draw
    from pilmoji.core import ColorT, FontT

__all__ = (
    'wrap_text',
)


def _pilmoji_parse_line(line: str, /) -> list[Node]:
    nodes = []

    for i, chunk in enumerate(EMOJI_REGEX.split(line)):
        if not chunk:
            continue

        if not i % 2:
            nodes.append(Node(NodeType.text, chunk))
            continue

        if len(chunk) > 18:  # This is guaranteed to be a Discord emoji
            node = Node(NodeType.discord_emoji, chunk)
        else:
            node = Node(NodeType.emoji, chunk)

        nodes.append(node)

    return nodes


def _to_emoji_aware_chars(text: str) -> list[str]:
    nodes = _pilmoji_parse_line(text)
    result = []

    for node in nodes:
        if node.type is NodeType.text:
            result.extend(node.content)
            continue

        result.append(node.content)

    return result


def _strip_split_text(text: list[str]) -> list[str]:
    """Note that this modifies in place"""
    if not text:
        return text

    text[0] = text[0].lstrip()
    text[-1] = text[-1].rstrip()

    if not text[0]:
        text.pop(0)

    if text and not text[-1]:
        text.pop(-1)

    return text


def _wrap_text_by_chars(text: str, max_width: int, to_getsize: Callable[[str], tuple[int, int]]) -> list[str]:
    result = []
    buffer = ''

    for char in _to_emoji_aware_chars(text):
        new = buffer + char

        width, _ = to_getsize(new)
        if width > max_width:
            result.append(buffer)
            buffer = char

            continue

        buffer += char

    if buffer:
        result.append(buffer)

    return result


def _wrap_line(text: str, font: FontT, max_width: int, **pilmoji_kwargs) -> list[str]:
    result = []
    buffer = []

    _getsize = partial(getsize, font=font, **pilmoji_kwargs)

    for word in text.split():
        new = ' '.join(buffer) + ' ' + word

        width, _ = _getsize(new)
        if width >= max_width:
            new = ' '.join(buffer)
            width, _ = _getsize(new)

            if width >= max_width:
                wrapped = _wrap_text_by_chars(new, max_width, _getsize)
                last = wrapped.pop()

                result += wrapped
                buffer = [last, word]

            else:
                result.append(new)
                buffer = [word]

            continue

        buffer.append(word)

    if buffer:
        new = ' '.join(buffer)
        width, _ = font.getsize(new)

        if width >= max_width:
            result += _wrap_text_by_chars(new, max_width, _getsize)
        else:
            result.append(new)

    return _strip_split_text(result)


def wrap_text(text: str, font: FontT, max_width: int) -> list[str]:
    lines = text.split('\n')
    result = []

    for line in lines:
        result += _wrap_line(line, font, max_width)

    return result


class FallbackFontSession:
    def __init__(self, font: FallbackFont, draw: Draw) -> None:
        self._font = font
        self._draw = draw

    def __enter__(self) -> FallbackFont:
        self._font.inject(self._draw)
        return self._font

    def __exit__(self, *args) -> None:
        self._font.eject(self._draw)


class FallbackFont:
    def __init__(
        self,
        font: FontT,
        fallback_loader: Callable[[], FontT],
        *,
        fallback_scale: float = 1,
        fallback_offset: tuple[int, int] = (0, 0),
    ) -> None:
        self._prepare(font, fallback_loader, fallback_scale, fallback_offset)
        self._load_font_regex()

    def _prepare(self, font, fallback_loader, fallback_scale, fallback_offset) -> None:
        self.font: FontT = font
        self.fallback_loader = fallback_loader
        self.fallback_scale: float = fallback_scale
        self.fallback_offset: tuple[int, int] = fallback_offset

        self._size: int = font.size
        self._fallback_size: int = round(self._size * fallback_scale)

        self._fallback: FontT | None = None
        self._regex: re.Pattern[str] = None  # type: ignore

    @property
    def fallback(self) -> FontT:
        if self._fallback is None:
            self._fallback = self.fallback_loader()

        return self._fallback

    @property
    def path(self) -> str:
        return self.font.path

    @property
    def size(self) -> int:
        return self._size

    def _load_font_regex(self) -> None:
        with TTFont(self.font.path) as font:
            characters = (chr(code) for table in font["cmap"].tables for code, _ in table.cmap.items())

        self._regex = re.compile('([^%s]+)' % ''.join(map(re.escape, characters)))

    def _split_text(self, text: str) -> Iterator[list[str]]:
        yield from (self._regex.split(line) for line in text.split('\n'))

    def variant(self, *, font: FontT = None, size: int = None) -> FallbackFont:
        if font is not None:
            font = font.path
            size = size or font.size

        new = self.__class__.__new__(self.__class__)
        new._prepare(
            self.font.font_variant(font=font, size=size), self.fallback_loader, self.fallback_scale, self.fallback_offset
        )

        new._fallback = self.fallback and self.fallback.font_variant(size=round(size * self.fallback_scale))
        new._regex = self._regex

        if font is not None or not new._regex:
            new._load_font_regex()

        return new

    def inject(self, draw: Draw) -> None:
        self.font.getsize, self.__font_getsize = self.getsize, self.font.getsize
        draw.text, self.__draw_text = partial(self.text, draw), draw.text

    def eject(self, draw: Draw) -> None:
        self.font.getsize = self.__font_getsize
        del self.__font_getsize

        draw.text = self.__draw_text
        del self.__draw_text

    def session(self, draw: Draw) -> FallbackFontSession:
        return FallbackFontSession(self, draw)

    def getsize(self, text: str) -> tuple[int, int]:
        width = height = 0

        for line in self._split_text(text):
            current = 0

            for i, chunk in enumerate(line):
                if not chunk:
                    continue

                font = self.fallback if i % 2 else self.font

                if font is self.font and font.getsize == self.getsize:
                    font_getsize = self.__font_getsize
                else:
                    font_getsize = font.getsize
                current += font_getsize(chunk)[0]

            if current > width:
                width = current

            height += 4 + self._size

        return width, height - 4

    def text(self, draw: Draw, xy: tuple[int, int], text: str, fill: ColorT = None, font: FontT = None, *args, **kwargs) -> None:
        if font is not None and (font.path, font.size) != (self.font.path, self.font.size) and font is not self:
            return self.variant(font=font).text(draw, xy, text, fill, *args, **kwargs)

        x, y = xy
        draw_text = self.__draw_text if isinstance(draw.text, partial) else draw.text

        for line in self._split_text(text):
            for i, chunk in enumerate(line):
                if not chunk:
                    continue

                if i % 2:
                    font = self.fallback
                    offset_x, offset_y = self.fallback_offset
                    position = x + offset_x, y + offset_y
                else:
                    font = self.font
                    position = x, y
                draw_text(position, chunk, fill, font, *args, **kwargs)

                if font is self.font and font.getsize == self.getsize:
                    font_getsize = self.__font_getsize
                else:
                    font_getsize = font.getsize

                width, _ = font_getsize(chunk)
                x += width

            y += 4 + self._size
            x = xy[0]
