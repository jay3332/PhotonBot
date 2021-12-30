from __future__ import annotations

import os
import aiohttp
import discord

from dotenv import load_dotenv
from discord.ext import commands
from jishaku.flags import Flags

from typing import TYPE_CHECKING

from .models import Context

__all__ = 'Photon',

load_dotenv()

Flags.NO_UNDERSCORE = True
Flags.NO_DM_TRACEBACK = True
Flags.HIDE = True

INTENTS = discord.Intents.default()  # For now

ALLOWED_MENTIONS = discord.AllowedMentions(
    users=True,
    roles=False,
    everyone=False,
    replied_user=False
)


class Photon(commands.Bot):
    ERROR_EMOJI = '<a:ferrisBongoHyper:878045828500029480>'

    if TYPE_CHECKING:
        session: aiohttp.ClientSession

    def __init__(self) -> None:
        super().__init__(
            command_prefix=self.__class__._get_prefix,
            case_insensitive=True,
            owner_id=414556245178056706,
            description='image manipulator',
            strip_after_prefix=True,
            allowed_mentions=ALLOWED_MENTIONS,
            intents=INTENTS,
            status=discord.Status.dnd,
            activity=discord.Activity(
                name='with images',
                type=discord.ActivityType.playing
            )
        )
        self.setup()

    async def _get_prefix(self, _message: discord.Message) -> list[str]:
        return ['photon', 'Photon', 'pt']  # Too lazy to make a decent prefix system so here you go

    def load_extensions(self) -> None:
        self.load_extension('jishaku')

        for extension in os.listdir('./bot/extensions'):
            if extension.endswith('.py') and not extension.startswith('_'):
                self.load_extension(f'bot.extensions.{extension[:-3]}')

    def setup(self) -> None:
        self.session = aiohttp.ClientSession()
        self.loop.create_task(self._dispatch_first_ready())
        self.load_extensions()

    async def _dispatch_first_ready(self) -> None:
        await self.wait_until_ready()
        self.dispatch('first_ready')

    async def on_first_ready(self) -> None:
        print(f'Logged in as {self.user} (ID: {self.user.id})')

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.BadArgument):
            return await ctx.send(f'{self.ERROR_EMOJI} {error}')

        error = getattr(error, 'original', error)

        if isinstance(error, discord.NotFound) and error.code == 10062:
            return

        await ctx.send(error)
        raise error

    async def process_commands(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        ctx = await self.get_context(message, cls=Context)
        await self.invoke(ctx)

    async def close(self) -> None:
        await self.session.close()
        await super().close()

    def run(self) -> None:
        try:
            super().run(os.environ['TOKEN'])
        except KeyError:
            raise ValueError('The "TOKEN" environment variable must be supplied.')
