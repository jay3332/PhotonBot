from __future__ import annotations

import discord
import time

from discord.context_managers import Typing
from discord.ext import commands


class Processing:
    EMOJI = '<a:ablobbouncefast:878313868340920391>'

    def __init__(self, ctx: commands.Context, /) -> None:
        self.ctx: commands.Context = ctx

        self._start: float = None
        self._message: discord.Message = None
        self._typing_ctx: Typing = None

    async def __aenter__(self) -> Processing:
        self._message = await self.ctx.reply(f'{self.EMOJI} Processing...')
        self._typing_ctx = ctx = self.ctx.typing()
        await ctx.__aenter__()

        self._start = time.perf_counter()
        return self

    async def __aexit__(self, *_) -> None:
        await self._message.delete(delay=0)
        await self._typing_ctx.__aexit__(None, None, None)

    async def __call__(self, file: discord.File, /) -> None:
        delta = time.perf_counter() - self._start

        embed = discord.Embed(color=0x2F3136, timestamp=self.ctx.message.created_at)
        embed.set_footer(text=f'{delta * 1000:.1f} ms', icon_url=self.ctx.author.avatar)
        embed.set_image(url='attachment://' + file.filename)

        await self.ctx.send(embed=embed, file=file)
