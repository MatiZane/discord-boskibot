from __future__ import annotations

import logging

import discord
from discord.ext import commands

from .ai_service import MikuAIService
from .config import BotConfig

log = logging.getLogger(__name__)

EXTENSIONS = (
    "miku_bot.cogs.ship",
    "miku_bot.cogs.ai",
    "miku_bot.cogs.music",
)


class MikuBot(commands.Bot):
    def __init__(self, config: BotConfig) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True

        super().__init__(
            command_prefix=config.command_prefix,
            intents=intents,
            help_command=commands.DefaultHelpCommand(no_category="Ogólne"),
        )
        self.config = config
        self.ai_service = MikuAIService(
            api_key=config.gemini_api_key,
            model=config.gemini_model,
            cooldown_seconds=config.ai_cooldown_seconds,
            history_turns=config.ai_history_turns,
        )

    async def setup_hook(self) -> None:
        for ext in EXTENSIONS:
            await self.load_extension(ext)
            log.info("Loaded extension: %s", ext)

        if self.config.guild_id is not None:
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("Synced %d slash commands to guild %s", len(synced), self.config.guild_id)
        else:
            synced = await self.tree.sync()
            log.info("Synced %d global slash commands", len(synced))

    async def on_ready(self) -> None:
        log.info("Miku Bot zalogowana jako %s (id=%s)", self.user, self.user.id if self.user else "?")
        log.info("FFmpeg: %s | AI aktywne: %s (%s)", self.config.ffmpeg_executable, self.ai_service.enabled, self.config.gemini_model)
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name="muzyki 🎧")
        )
