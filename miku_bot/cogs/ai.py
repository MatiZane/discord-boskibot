from __future__ import annotations

import logging

import discord
from discord.ext import commands

from ..ai_service import MikuAIService

log = logging.getLogger(__name__)


class MikuAICog(commands.Cog):
    def __init__(self, bot: commands.Bot, ai_service: MikuAIService) -> None:
        self.bot = bot
        self.ai = ai_service

    @commands.hybrid_command(
        name="miku",
        aliases=["ask", "zapytaj"],
        description="Porozmawiaj z Miku Nakano (mini AI)",
    )
    async def miku(self, ctx: commands.Context, *, pytanie: str) -> None:
        await ctx.defer()
        cleaned = self.ai.clean_prompt(pytanie, self.bot.user.id if self.bot.user else None)
        answer = await self.ai.reply(
            channel_id=ctx.channel.id,
            user_id=ctx.author.id,
            author_name=ctx.author.display_name,
            prompt=cleaned,
        )
        await ctx.send(answer, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(
        name="miku_reset",
        aliases=["mikureset", "resetmiku"],
        description="Wyczyść pamięć rozmowy Miku na tym kanale",
    )
    async def miku_reset(self, ctx: commands.Context) -> None:
        self.ai.reset_channel(ctx.channel.id)
        await ctx.send("W porządku, zaczynamy rozmowę od czystej kartki na tym kanale. 🎧")

    @miku.error
    async def miku_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            prefix = self.bot.config.command_prefix  # type: ignore[attr-defined]
            await ctx.send(f"Napisz coś po komendzie, np. `{prefix}miku polecisz coś spokojnego do słuchania?` 🎧")
            return
        log.exception("Miku AI command error: %s", error)
        await ctx.send("Coś poszło nie tak z odpowiedzią… spróbuj jeszcze raz.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or self.bot.user is None:
            return
        if message.mention_everyone:
            return

        prefix = self.bot.config.command_prefix  # type: ignore[attr-defined]
        if message.content.startswith(prefix):
            return

        mentioned = self.bot.user in message.mentions
        replied_to_bot = False
        if message.reference and message.reference.message_id:
            ref = message.reference.resolved
            if isinstance(ref, discord.Message) and ref.author.id == self.bot.user.id:
                replied_to_bot = True

        if not mentioned and not replied_to_bot:
            return

        cleaned = self.ai.clean_prompt(message.content, self.bot.user.id)
        async with message.channel.typing():
            answer = await self.ai.reply(
                channel_id=message.channel.id,
                user_id=message.author.id,
                author_name=message.author.display_name,
                prompt=cleaned,
            )
        await message.reply(
            answer,
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MikuAICog(bot, bot.ai_service))  # type: ignore[attr-defined]
