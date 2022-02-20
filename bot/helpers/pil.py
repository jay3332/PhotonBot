from __future__ import annotations

from functools import partial
from typing import Callable, TYPE_CHECKING

from pilmoji import EMOJI_REGEX, Node, NodeType, getsize

if TYPE_CHECKING:
    from pilmoji.core import FontT

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
