from __future__ import annotations

import discord
from discord.ext import commands


class InfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="strona",
        aliases=["web", "komendy", "link"],
        description="Pokaż link do strony z komendami i funkcjami Miku Bota",
    )
    async def strona(self, ctx: commands.Context) -> None:
        url = self.bot.config.site_url  # type: ignore[attr-defined]
        embed = discord.Embed(
            title="🎧 Miku Bot — Przewodnik serwera",
            description=(
                "Pełna lista komend (`!` i `/`), podgląd kart Ship oraz opis wszystkich funkcji:\n"
                f"**{url}**"
            ),
            color=discord.Color.from_rgb(125, 196, 245),
        )
        embed.add_field(name="Muzyka", value="`!p <tytuł/link>` · `/play` · `/speed`", inline=True)
        embed.add_field(name="Ship", value="`!s @nick1 nick2` · `/ship`", inline=True)
        embed.add_field(name="Mini-AI", value="`@Miku` · `!miku` · `/miku`", inline=True)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(InfoCog(bot))
