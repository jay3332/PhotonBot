import asyncio
import functools
import re

from urllib.parse import quote_plus
from typing import Awaitable, Callable, TypeVar

R = TypeVar('R')
EMOJI_REGEX = re.compile(r'<(a)?:([a-zA-Z0-9_]{2,32}):([0-9]{17,25})>')

__all__ = (
    'proportionally_scale',
    'to_thread',
    'url_from_emoji'
)


def to_thread(func: Callable[..., R]) -> Callable[..., Awaitable[R]]:
    """Moves this function's callback into a thread."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Awaitable[R]:
        return asyncio.to_thread(func, *args, **kwargs)

    return wrapper


def proportionally_scale(
    old: tuple[int, int],
    *,
    min_dimension: int = None,
    max_dimension: int = 600
) -> tuple[int, int]:
    """Scales the given dimensions proportionally to meet the specified
    minimum and maximum dimensions.

    Instead of a fixed point, this will ensure aspect ratio is kept.
    """

    width, height = old

    if min_dimension is not None:
        if width < min_dimension:
            width, height = min_dimension, int(height / (width / min_dimension))
        elif height < min_dimension:
            width, height = int(width / (height / min_dimension)), min_dimension

    if width > max_dimension:
        return max_dimension, int(height / (width / max_dimension))
    elif height > max_dimension:
        return int(width / (height / max_dimension)), max_dimension

    return width, height


def url_from_emoji(emoji: str, /) -> str:
    """Converts an emoji into a URL."""
    if match := EMOJI_REGEX.match(emoji):
        animated, _, id = match.groups()
        extension = 'gif' if animated else 'png'
        return f'https://cdn.discordapp.com/emojis/{id}.{extension}?v=1'
    else:
        fmt = 'https://emojicdn.elk.sh/{}?style=twitter'
        return fmt.format(quote_plus(emoji))
