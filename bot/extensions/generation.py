import discord

from discord.ext import commands
from typing import Optional, Union

from .. import Cog, Context, Photon
from ..features import *
from ..helpers import ImageFinder, url_from_emoji


class TryLink(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> Union[bytes, str]:
        if len(argument) < 8:
            async with ctx.bot.session.get(url_from_emoji(argument)) as response:
                if response.ok:
                    return await response.read()

        if not ImageFinder.URL_REGEX.match(argument.strip('<>')):
            raise commands.BadArgument('Invalid image URL.')

        return argument


class ImageGeneration(Cog, name='Image Generation'):
    """Generates images/gifs."""

    _CONVERTER = Optional[
        Union[
            discord.Member,
            discord.Emoji,
            discord.PartialEmoji,
            TryLink
        ]
    ]

    def __setup__(self) -> None:
        self.finder: ImageFinder = ImageFinder()

    @commands.command('caption')
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def caption(self, ctx: Context, image: _CONVERTER, *, caption: str) -> None:
        image = await self.finder.find(ctx, image, run_conversions=False)

        async with ctx.processing() as callback:
            async with IFunnyCaption(image, text=caption) as caption:
                await callback(await caption.render())

        del caption


def setup(bot: Photon) -> None:
    bot.add_cog(ImageGeneration(bot))
