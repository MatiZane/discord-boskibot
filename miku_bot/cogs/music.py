from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from ..bot import IDLE_ACTIVITY
from ..music_engine import (
    DEFAULT_SPEED,
    MAX_SPEED,
    MIN_SPEED,
    GuildMusicState,
    Track,
    build_ffmpeg_options,
    clamp_speed,
    extract_tracks,
    format_duration,
    format_speed,
    resolve_stream,
)

log = logging.getLogger(__name__)


class PlayerControlsView(discord.ui.View):
    def __init__(self, cog: MusicCog, guild_id: int) -> None:
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id

    async def _check_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        guild = interaction.guild
        if guild is None or guild.voice_client is None:
            await interaction.response.send_message("Nie jestem obecnie na żadnym kanale głosowym.", ephemeral=True)
            return None
        member = interaction.user
        if not isinstance(member, discord.Member) or member.voice is None or member.voice.channel != guild.voice_client.channel:
            await interaction.response.send_message("Dołącz najpierw na mój kanał głosowy, żeby sterować odtwarzaczem.", ephemeral=True)
            return None
        return guild.voice_client  # type: ignore[return-value]

    @discord.ui.button(label="Pauza / Wznów", emoji="⏯️", style=discord.ButtonStyle.secondary)
    async def toggle_pause(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        vc = await self._check_voice(interaction)
        if vc is None:
            return
        if vc.is_paused():
            vc.resume()
            await interaction.response.send_message("Wznowiono odtwarzanie. 🎧", ephemeral=True)
        elif vc.is_playing():
            vc.pause()
            await interaction.response.send_message("Wstrzymano odtwarzanie.", ephemeral=True)
        else:
            await interaction.response.send_message("Nic teraz nie gra.", ephemeral=True)

    @discord.ui.button(label="Pomiń", emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def skip_btn(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        vc = await self._check_voice(interaction)
        if vc is None:
            return
        state = self.cog.get_state(self.guild_id)
        state.loop_track = False
        if vc.is_playing() or vc.is_paused():
            vc.stop()
            await interaction.response.send_message("Pomijam obecny utwór.", ephemeral=True)
        else:
            await interaction.response.send_message("Kolejka jest pusta.", ephemeral=True)

    @discord.ui.button(label="Pętla", emoji="🔁", style=discord.ButtonStyle.secondary)
    async def loop_btn(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        vc = await self._check_voice(interaction)
        if vc is None:
            return
        state = self.cog.get_state(self.guild_id)
        state.loop_track = not state.loop_track
        status = "włączona 🔁" if state.loop_track else "wyłączona"
        await interaction.response.send_message(f"Pętla obecnego utworu: **{status}**.", ephemeral=True)

    @discord.ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop_btn(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        vc = await self._check_voice(interaction)
        if vc is None:
            return
        state = self.cog.get_state(self.guild_id)
        state.clear()
        state.cancel_idle_timer()
        vc.stop()
        await vc.disconnect(force=False)
        await self.cog.bot.change_presence(activity=IDLE_ACTIVITY)
        await interaction.response.send_message("Zatrzymałam muzykę i opuściłam kanał głosowy.", ephemeral=True)


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._states: dict[int, GuildMusicState] = {}

    def get_state(self, guild_id: int) -> GuildMusicState:
        state = self._states.get(guild_id)
        if state is None:
            state = GuildMusicState(guild_id=guild_id)
            self._states[guild_id] = state
        return state

    async def _ensure_voice(self, ctx: commands.Context) -> discord.VoiceClient | None:
        if ctx.guild is None:
            await ctx.send("Muzykę mogę puszczać tylko na serwerze (na kanale głosowym).")
            return None
        if not isinstance(ctx.author, discord.Member) or ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send("Wejdź najpierw na kanał głosowy, a dołączę do Ciebie. 🎧")
            return None

        target_channel = ctx.author.voice.channel
        vc = ctx.guild.voice_client
        if vc is None:
            return await target_channel.connect(self_deaf=True)
        if vc.channel != target_channel:
            await vc.move_to(target_channel)
        return vc  # type: ignore[return-value]

    def _build_now_playing_embed(self, track: Track, state: GuildMusicState) -> discord.Embed:
        embed = discord.Embed(
            title=track.title,
            url=track.webpage_url,
            color=discord.Color.from_rgb(125, 196, 245),
        )
        embed.set_author(name="🎧 Teraz odtwarzane")
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        embed.add_field(name="Czas", value=format_duration(track.duration), inline=True)
        embed.add_field(name="Prędkość", value=format_speed(state.speed), inline=True)
        embed.add_field(name="Pętla", value="Włączona 🔁" if state.loop_track else "Wyłączona", inline=True)
        footer = f"Dodał(a): {track.requester}"
        if track.uploader:
            footer += f" · {track.uploader}"
        embed.set_footer(text=footer)
        return embed

    def _schedule_idle_disconnect(self, guild: discord.Guild, state: GuildMusicState) -> None:
        state.cancel_idle_timer()
        idle_seconds = self.bot.config.voice_idle_seconds  # type: ignore[attr-defined]

        async def _idle() -> None:
            try:
                await asyncio.sleep(idle_seconds)
                vc = guild.voice_client
                if vc is not None and not vc.is_playing() and not vc.is_paused():
                    state.clear()
                    await vc.disconnect(force=False)
                    if state.text_channel_id:
                        ch = guild.get_channel(state.text_channel_id)
                        if isinstance(ch, discord.abc.Messageable):
                            await ch.send("Zrobiło się cicho na kanale, więc schowałam słuchawki i wyszłam. 🎧")
            except asyncio.CancelledError:
                return
            except Exception as exc:
                log.debug("Idle disconnect error: %s", exc)

        state.idle_task = asyncio.create_task(_idle())

    async def _play_next(self, guild: discord.Guild) -> None:
        state = self.get_state(guild.id)
        async with state.lock:
            vc = guild.voice_client
            if vc is None or not vc.is_connected():
                state.clear()
                return
            if vc.is_playing() or vc.is_paused():
                return

            next_item = state.next_track()
            if next_item is None:
                await self.bot.change_presence(activity=IDLE_ACTIVITY)
                self._schedule_idle_disconnect(guild, state)
                return

            state.cancel_idle_timer()
            try:
                resolved = await resolve_stream(next_item)
                state.current = resolved
                before_opts, ff_opts = build_ffmpeg_options(state.speed)
                source = discord.FFmpegOpusAudio(
                    resolved.stream_url,
                    executable=self.bot.config.ffmpeg_executable,  # type: ignore[attr-defined]
                    before_options=before_opts,
                    options=ff_opts,
                )
            except Exception as exc:
                log.warning("Failed to play track %s: %s", next_item.title, exc)
                if state.text_channel_id:
                    ch = guild.get_channel(state.text_channel_id)
                    if isinstance(ch, discord.abc.Messageable):
                        await ch.send(f"Nie udało się odtworzyć **{next_item.title}** — przechodzę do kolejnego utworu.")
                state.loop_track = False
                asyncio.create_task(self._play_next(guild))
                return

            def _after(error: Exception | None) -> None:
                if error:
                    log.warning("Audio playback finished with error: %s", error)
                asyncio.run_coroutine_threadsafe(self._play_next(guild), self.bot.loop)

            vc.play(source, after=_after)
            await self.bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.listening, name=resolved.title[:100])
            )

            if state.text_channel_id:
                ch = guild.get_channel(state.text_channel_id)
                if isinstance(ch, discord.abc.Messageable):
                    await ch.send(
                        embed=self._build_now_playing_embed(resolved, state),
                        view=PlayerControlsView(self, guild.id),
                    )

    @commands.hybrid_command(
        name="play",
        aliases=["p"],
        description="Odtwórz utwór, YouTube Shorts, playlistę lub wyszukaj po tytule",
    )
    async def play(self, ctx: commands.Context, *, zapytanie: str) -> None:
        await ctx.defer()
        vc = await self._ensure_voice(ctx)
        if vc is None or ctx.guild is None:
            return

        state = self.get_state(ctx.guild.id)
        state.text_channel_id = ctx.channel.id

        try:
            tracks, playlist_title = await extract_tracks(zapytanie, ctx.author.display_name)
        except Exception as exc:
            await ctx.send(f"Nie mogłam tego wczytać: {exc}")
            return

        was_busy = vc.is_playing() or vc.is_paused() or state.current is not None
        queue_len = state.enqueue(tracks)

        if playlist_title and len(tracks) > 1:
            await ctx.send(f"🎶 Dodano playlistę **{playlist_title}** ({len(tracks)} utworów) do kolejki.")
        elif was_busy:
            first = tracks[0]
            await ctx.send(f"🎶 Dodano do kolejki (#{queue_len}): **{first.title}** ({format_duration(first.duration)})")
        else:
            await ctx.send(f"🎶 Przygotowuję: **{tracks[0].title}**…")

        if not vc.is_playing() and not vc.is_paused():
            await self._play_next(ctx.guild)

    @commands.hybrid_command(name="skip", aliases=["snext", "next"], description="Pomiń aktualny utwór")
    async def skip(self, ctx: commands.Context) -> None:
        if ctx.guild is None or ctx.guild.voice_client is None:
            await ctx.send("Nic teraz nie odtwarzam.")
            return
        vc = ctx.guild.voice_client
        state = self.get_state(ctx.guild.id)
        state.loop_track = False
        if vc.is_playing() or vc.is_paused():
            vc.stop()
            await ctx.send("⏭️ Pominięto utwór.")
        else:
            await ctx.send("Kolejka jest pusta.")

    @commands.hybrid_command(name="pause", description="Wstrzymaj odtwarzanie")
    async def pause(self, ctx: commands.Context) -> None:
        vc = ctx.guild.voice_client if ctx.guild else None
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("⏸️ Wstrzymano muzykę.")
        else:
            await ctx.send("Nic teraz nie gra.")

    @commands.hybrid_command(name="resume", description="Wznów wstrzymane odtwarzanie")
    async def resume(self, ctx: commands.Context) -> None:
        vc = ctx.guild.voice_client if ctx.guild else None
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send("▶️ Wznowiono muzykę.")
        else:
            await ctx.send("Odtwarzacz nie jest wstrzymany.")

    @commands.hybrid_command(name="queue", aliases=["q", "kolejka"], description="Pokaż kolejkę utworów")
    async def queue(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        state = self.get_state(ctx.guild.id)
        lines: list[str] = []
        if state.current:
            lines.append(f"**Teraz gra:** [{state.current.title}]({state.current.webpage_url}) ({format_duration(state.current.duration)})")
        if state.queue:
            lines.append("")
            for idx, track in enumerate(list(state.queue)[:10], start=1):
                lines.append(f"`{idx}.` {track.title} ({format_duration(track.duration)})")
            if len(state.queue) > 10:
                lines.append(f"… i jeszcze {len(state.queue) - 10} utworów.")
        if not lines:
            await ctx.send("Kolejka jest pusta. Wrzuć coś przez `!p <tytuł lub link>`. 🎧")
            return
        embed = discord.Embed(
            title="🎶 Kolejka odtwarzania",
            description="\n".join(lines),
            color=discord.Color.from_rgb(125, 196, 245),
        )
        embed.set_footer(text=f"Prędkość: {format_speed(state.speed)} · Pętla: {'Wł.' if state.loop_track else 'Wył.'}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="loop", description="Przełącz powtarzanie obecnego utworu")
    async def loop(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        state = self.get_state(ctx.guild.id)
        state.loop_track = not state.loop_track
        await ctx.send(f"🔁 Pętla obecnego utworu: **{'włączona' if state.loop_track else 'wyłączona'}**.")

    @commands.hybrid_command(
        name="speed",
        aliases=["predkosc"],
        description=f"Ustaw prędkość odtwarzania ({MIN_SPEED}–{MAX_SPEED}, naturalna tonacja)",
    )
    async def speed(self, ctx: commands.Context, wartosc: float = DEFAULT_SPEED) -> None:
        if ctx.guild is None:
            return
        state = self.get_state(ctx.guild.id)
        state.speed = clamp_speed(wartosc)
        extra = " (zadziała od następnego utworu)" if state.current else ""
        await ctx.send(f"⏩ Prędkość odtwarzania ustawiona na **{format_speed(state.speed)}** (naturalna tonacja){extra}.")

    @commands.hybrid_command(name="stop", aliases=["leave", "dc"], description="Zatrzymaj muzykę i wyjdź z kanału")
    async def stop(self, ctx: commands.Context) -> None:
        if ctx.guild is None or ctx.guild.voice_client is None:
            await ctx.send("Nie jestem na żadnym kanale głosowym.")
            return
        state = self.get_state(ctx.guild.id)
        state.clear()
        state.cancel_idle_timer()
        vc = ctx.guild.voice_client
        vc.stop()
        await vc.disconnect(force=False)
        await self.bot.change_presence(activity=IDLE_ACTIVITY)
        await ctx.send("⏹️ Zatrzymano muzykę i wyczyszczono kolejkę.")

    @play.error
    async def play_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            prefix = self.bot.config.command_prefix  # type: ignore[attr-defined]
            await ctx.send(f"Podaj link YouTube (może być Shorts/playlista) albo tytuł, np. `{prefix}p gotoubun no kimochi`.")
            return
        log.exception("Play error: %s", error)
        await ctx.send("Wystąpił błąd podczas uruchamiania muzyki.")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot or before.channel == after.channel:
            return
        guild = member.guild
        vc = guild.voice_client
        if vc is None or vc.channel is None:
            return
        humans = [m for m in vc.channel.members if not m.bot]
        if not humans:
            state = self.get_state(guild.id)
            state.clear()
            state.cancel_idle_timer()
            vc.stop()
            await vc.disconnect(force=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicCog(bot))
