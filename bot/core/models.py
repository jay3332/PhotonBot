from __future__ import annotations

from discord.ext import commands
from discord.utils import maybe_coroutine

from typing import Awaitable, Union, TYPE_CHECKING

from ..helpers.context_managers import Processing

if TYPE_CHECKING:
    from .. import Photon

__all__ = (
    'Cog',
    'Context'
)


class Cog(commands.Cog):
    def __init__(self, bot: Photon, /) -> None:
        self.bot: Photon = bot
        bot.loop.create_task(maybe_coroutine(self.__setup__))

    def __setup__(self) -> Union[None, Awaitable[None]]:
        ...


class Context(commands.Context):
    def processing(self) -> Processing:
        return Processing(self)
