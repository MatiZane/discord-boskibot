from __future__ import annotations

import logging
import re

import discord
from discord.ext import commands

from ..ship_logic import calculate_ship, format_display_name, normalize_ship_key

log = logging.getLogger(__name__)

_MENTION_RE = re.compile(r"^<@!?(\d+)>$")


class ShipCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _resolve_target(self, ctx: commands.Context, raw: str) -> tuple[str, str, str]:
        """Return (display_name, mention_or_display, canonical_key)."""
        text = raw.strip()
        member: discord.abc.User | None = None

        match = _MENTION_RE.match(text)
        if match:
            uid = int(match.group(1))
            if ctx.guild is not None:
                member = ctx.guild.get_member(uid)
            if member is None:
                member = self.bot.get_user(uid)
            if member is None:
                try:
                    member = await self.bot.fetch_user(uid)
                except Exception:
                    member = None
        elif ctx.guild is not None:
            lowered = normalize_ship_key(text)
            for candidate in ctx.guild.members:
                if (
                    candidate.name.lower() == lowered
                    or candidate.display_name.lower() == lowered
                ):
                    member = candidate
                    break

        if member is not None:
            return member.display_name, member.mention, member.name

        display = format_display_name(text)
        return display, display, text

    def _pick_emoji(self, guild: discord.Guild | None, tier: str) -> str:
        cfg = self.bot.config  # type: ignore[attr-defined]
        configured = {
            "high": cfg.ship_emoji_high,
            "mid": cfg.ship_emoji_mid,
            "low": cfg.ship_emoji_low,
        }.get(tier, "")
        if configured:
            return configured

        if guild is not None:
            keywords = {
                "high": ("miku_heart", "heart", "serduszko", "love", "hap"),
                "mid": ("mikuok", "blush", "macha", "mmm", "thx"),
                "low": ("sigh", "pout", "sad", "destroyer", "fing"),
            }.get(tier, ())
            miku_emojis = [e for e in guild.emojis if e.available and "miku" in e.name.lower()]
            for kw in keywords:
                for emoji in miku_emojis:
                    if kw in emoji.name.lower():
                        return str(emoji)
            if miku_emojis:
                return str(miku_emojis[0])

        return {"high": "💙", "mid": "✨", "low": "🎧"}.get(tier, "💙")

    @commands.hybrid_command(
        name="ship",
        aliases=["s"],
        description="Sprawdź stałą zgodność dwóch osób, nicków lub haseł",
    )
    async def ship(
        self,
        ctx: commands.Context,
        osoba1: str,
        *,
        osoba2: str | None = None,
    ) -> None:
        if osoba2 is None or not osoba2.strip():
            disp_a, label_a, key_a = ctx.author.display_name, ctx.author.mention, ctx.author.name
            disp_b, label_b, key_b = await self._resolve_target(ctx, osoba1)
        else:
            disp_a, label_a, key_a = await self._resolve_target(ctx, osoba1)
            disp_b, label_b, key_b = await self._resolve_target(ctx, osoba2)

        result = calculate_ship(disp_a, disp_b, key_a=key_a, key_b=key_b)
        emoji = self._pick_emoji(ctx.guild, result.tier)
        em_suffix = f"{emoji} {emoji}" if result.percent >= 80 else emoji
        headline = f"{label_a} i {label_b} mają **{result.percent}%** zgodności {em_suffix}"

        await ctx.send(
            content=headline,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )

    @ship.error
    async def ship_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            prefix = self.bot.config.command_prefix  # type: ignore[attr-defined]
            await ctx.send(f"Użycie: `{prefix}s @nick1 nick2` albo `{prefix}s hasło` (wtedy paruję z Tobą).")
            return
        log.exception("Ship command error: %s", error)
        await ctx.send("Nie udało się policzyć zgodności… spróbuj jeszcze raz.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ShipCog(bot))
