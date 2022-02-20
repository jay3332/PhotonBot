from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pilmoji.core import FontT

__all__ = (
    'wrap_text',
)


def _strip_split_text(text: list[str]) -> list[str]:
    """Note that this modifies in place"""
    if not text:
        return text

    text[0] = text[0].lstrip()
    text[-1] = text[-1].rstrip()

    return text


def _wrap_text_by_chars(text: str, font: FontT, max_width: int) -> list[str]:
    result = []
    buffer = ''

    for char in text:
        new = buffer + char

        width, _ = font.getsize(new)
        if width > max_width:
            result.append(buffer)
            buffer = char

            continue

        buffer += char

    if buffer:
        result.append(buffer)

    return result


def _wrap_line(text: str, font: FontT, max_width: int) -> list[str]:
    result = []
    buffer = []

    for word in text.split():
        new = ' '.join(buffer) + ' ' + word

        width, _ = font.getsize(new)
        if width >= max_width:
            new = ' '.join(buffer)
            width, _ = font.getsize(new)

            if width >= max_width:
                wrapped = _wrap_text_by_chars(new, font, max_width)
                last = wrapped.pop()

                result += wrapped
                buffer = [last]

            else:
                result.append(new)
                buffer = [word]

            continue

        buffer.append(word)

    if buffer:
        new = ' '.join(buffer)
        width, _ = font.getsize(new)

        if width >= max_width:
            result += _wrap_text_by_chars(new, font, max_width)
        else:
            result.append(new)

    return _strip_split_text(result)


def wrap_text(text: str, font: FontT, max_width: int) -> list[str]:
    lines = text.split('\n')
    result = []

    for line in lines:
        result += _wrap_line(line, font, max_width)

    return result
