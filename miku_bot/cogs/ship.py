from __future__ import annotations

import asyncio
import io
import logging
import re

import discord
from discord.ext import commands

from ..ship_card import render_ship_card
from ..ship_logic import calculate_ship, format_display_name, normalize_ship_key

log = logging.getLogger(__name__)

_MENTION_RE = re.compile(r"^<@!?(\d+)>$")


class ShipCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _resolve_target(
        self, ctx: commands.Context, raw: str
    ) -> tuple[str, str, str, bytes | None]:
        """Return (display_name, mention_or_display, canonical_key, avatar_bytes)."""
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
            avatar_bytes: bytes | None = None
            try:
                avatar_bytes = await asyncio.wait_for(
                    member.display_avatar.with_size(256).with_format("png").read(),
                    timeout=4.0,
                )
            except Exception as exc:
                log.debug("Could not fetch avatar for %s: %s", member, exc)
            return member.display_name, member.mention, member.name, avatar_bytes

        display = format_display_name(text)
        return display, display, text, None

    async def _author_target(self, ctx: commands.Context) -> tuple[str, str, str, bytes | None]:
        author = ctx.author
        avatar_bytes: bytes | None = None
        try:
            avatar_bytes = await asyncio.wait_for(
                author.display_avatar.with_size(256).with_format("png").read(),
                timeout=4.0,
            )
        except Exception:
            pass
        return author.display_name, author.mention, author.name, avatar_bytes

    def _pick_emoji(self, guild: discord.Guild | None, tier: str) -> str:
        cfg = self.bot.config  # type: ignore[attr-defined]
        configured = {
            "high": cfg.ship_emoji_high,
            "mid": cfg.ship_emoji_mid,
            "low": cfg.ship_emoji_low,
        }.get(tier, "")
        if configured:
            return configured

        if guild is not None and tier == "high":
            for emoji in guild.emojis:
                if emoji.available and "miku" in emoji.name.lower() and (
                    "heart" in emoji.name.lower() or "serce" in emoji.name.lower() or "love" in emoji.name.lower()
                ):
                    return str(emoji)
            for emoji in guild.emojis:
                if emoji.available and "miku" in emoji.name.lower():
                    return str(emoji)

        return {"high": "💙", "mid": "✨", "low": "🎧"}.get(tier, "💙")

    @commands.hybrid_command(
        name="ship",
        aliases=["s"],
        description="Sprawdź stałą zgodność dwóch osób (nicków lub @wzmianek) z kartą graficzną",
    )
    async def ship(
        self,
        ctx: commands.Context,
        osoba1: str,
        *,
        osoba2: str | None = None,
    ) -> None:
        await ctx.defer()

        if osoba2 is None or not osoba2.strip():
            disp_a, label_a, key_a, avatar_a = await self._author_target(ctx)
            disp_b, label_b, key_b, avatar_b = await self._resolve_target(ctx, osoba1)
        else:
            disp_a, label_a, key_a, avatar_a = await self._resolve_target(ctx, osoba1)
            disp_b, label_b, key_b, avatar_b = await self._resolve_target(ctx, osoba2)

        result = calculate_ship(disp_a, disp_b, key_a=key_a, key_b=key_b)
        card_bytes = await asyncio.to_thread(render_ship_card, result, avatar_a, avatar_b)

        emoji = self._pick_emoji(ctx.guild, result.tier)
        em_suffix = f"{emoji} {emoji}" if result.percent >= 80 else emoji
        headline = f"{label_a} i {label_b} mają **{result.percent}%** zgodności {em_suffix}"

        file = discord.File(io.BytesIO(card_bytes), filename="miku-ship.png")
        await ctx.send(
            content=headline,
            file=file,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )

    @ship.error
    async def ship_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            prefix = self.bot.config.command_prefix  # type: ignore[attr-defined]
            await ctx.send(f"Użycie: `{prefix}s @nick1 nick2` albo `{prefix}s nick` (wtedy paruję z Tobą).")
            return
        log.exception("Ship command error: %s", error)
        await ctx.send("Nie udało się wygenerować karty zgodności… spróbuj jeszcze raz.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ShipCog(bot))
