from __future__ import annotations

import asyncio
import logging
import pathlib
import platform
import re
import shlex
from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urlparse

import discord
import yt_dlp

log = logging.getLogger(__name__)

MIN_SPEED = 0.5
MAX_SPEED = 2.0
DEFAULT_SPEED = 1.0
MAX_PLAYLIST_ITEMS = 50

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)

YTDL_BASE_OPTS: dict[str, object] = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch1",
    "source_address": "0.0.0.0",
    "extract_flat": "in_playlist",
    "skip_download": True,
    "playlistend": MAX_PLAYLIST_ITEMS,
}

YTDL_RESOLVE_OPTS: dict[str, object] = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
    "skip_download": True,
}


@dataclass(frozen=True)
class Track:
    title: str
    webpage_url: str
    requester: str
    duration: int | None = None
    uploader: str | None = None
    thumbnail: str | None = None
    stream_url: str | None = None
    user_agent: str | None = None


def ensure_opus_loaded() -> bool:
    """Explicitly load bundled libopus DLL from discord.py on Windows when not yet loaded."""
    if discord.opus.is_loaded():
        return True
    bin_dir = pathlib.Path(discord.__file__).parent / "bin"
    arch = "x64" if platform.machine().endswith("64") or platform.architecture()[0] == "64bit" else "x86"
    candidates = [
        bin_dir / f"libopus-0.{arch}.dll",
        bin_dir / "libopus-0.x64.dll",
        bin_dir / "libopus-0.x86.dll",
    ]
    for path in candidates:
        if path.is_file():
            try:
                discord.opus.load_opus(str(path))
                if discord.opus.is_loaded():
                    log.info("Loaded Opus library: %s", path.name)
                    return True
            except Exception as exc:
                log.warning("Failed to load Opus from %s: %s", path, exc)
    return discord.opus.is_loaded()


def clamp_speed(value: float) -> float:
    if value != value or value in (float("inf"), float("-inf")):
        return DEFAULT_SPEED
    bounded = min(MAX_SPEED, max(MIN_SPEED, value))
    rounded = round(bounded, 2)
    return DEFAULT_SPEED if abs(rounded - DEFAULT_SPEED) < 0.005 else rounded


def format_speed(value: float) -> str:
    safe = clamp_speed(value)
    if abs(safe - round(safe)) < 0.005:
        return f"{int(round(safe))}×"
    text = f"{safe:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{text}×"


def format_duration(seconds: int | None) -> str:
    if not seconds or seconds <= 0:
        return "na żywo / nieznany"
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def normalize_query(raw: str) -> str:
    """Keep valid http(s) URLs (including YouTube Shorts/playlists); wrap plain text as ytsearch1."""
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("Podaj link YouTube albo nazwę utworu.")
    if _URL_RE.match(cleaned):
        parsed = urlparse(cleaned)
        if not parsed.netloc:
            raise ValueError("Ten link wygląda na niepoprawny.")
        return cleaned
    return f"ytsearch1:{cleaned}"


def build_ffmpeg_options(speed: float = DEFAULT_SPEED, user_agent: str | None = None) -> tuple[str, str]:
    """Build reconnect-safe FFmpeg before_options and audio filter options (normal pitch)."""
    before = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    if user_agent and user_agent.strip():
        before += f" -user_agent {shlex.quote(user_agent.strip())}"
    safe = clamp_speed(speed)
    if abs(safe - DEFAULT_SPEED) < 0.005:
        return before, "-vn"
    return before, f"-vn -af atempo={safe:.2f}"


def _entry_to_track(entry: dict, requester: str) -> Track | None:
    if not entry:
        return None
    title = str(entry.get("title") or "Bez tytułu").strip()
    webpage_url = entry.get("webpage_url") or entry.get("original_url") or entry.get("url")
    if not webpage_url:
        return None
    webpage_url = str(webpage_url)
    if not _URL_RE.match(webpage_url):
        # Flat playlist entry often stores bare video ID
        webpage_url = f"https://www.youtube.com/watch?v={webpage_url}"

    stream_url = str(entry["url"]) if entry.get("url") and entry.get("acodec") not in (None, "none") else None
    if stream_url and stream_url == webpage_url and "youtube.com" in stream_url:
        stream_url = None

    duration_raw = entry.get("duration")
    duration = int(duration_raw) if isinstance(duration_raw, (int, float)) and duration_raw > 0 else None
    uploader = str(entry.get("uploader") or entry.get("channel") or "").strip() or None
    thumbnail = str(entry.get("thumbnail") or "").strip() or None

    headers = entry.get("http_headers") if isinstance(entry.get("http_headers"), dict) else {}
    user_agent = str(headers.get("User-Agent") or "").strip() or None

    return Track(
        title=title,
        webpage_url=webpage_url,
        requester=requester,
        duration=duration,
        uploader=uploader,
        thumbnail=thumbnail,
        stream_url=stream_url,
        user_agent=user_agent,
    )


def _extract_sync(query: str, requester: str) -> tuple[list[Track], str | None]:
    target = normalize_query(query)
    with yt_dlp.YoutubeDL(YTDL_BASE_OPTS) as ydl:
        info = ydl.extract_info(target, download=False)
    if not info:
        raise ValueError("Nie znalazłam takiego utworu na YouTube.")

    if "entries" in info and info["entries"] is not None:
        raw_entries = [e for e in info["entries"] if e]
        is_search = target.startswith("ytsearch")
        if is_search:
            raw_entries = raw_entries[:1]
        tracks = [t for e in raw_entries if (t := _entry_to_track(e, requester)) is not None]
        if not tracks:
            if is_search:
                raise ValueError("Wyszukiwanie YouTube po samej nazwie nie zwróciło wyników — wklej bezpośredni link z YouTube.")
            raise ValueError("Nie znalazłam żadnego dostępnego utworu.")
        playlist_title = None if is_search else (str(info.get("title") or "").strip() or None)
        return tracks, playlist_title

    track = _entry_to_track(info, requester)
    if track is None:
        raise ValueError("Nie udało się odczytać danych tego utworu.")
    return [track], None


def _resolve_stream_sync(track: Track) -> Track:
    with yt_dlp.YoutubeDL(YTDL_RESOLVE_OPTS) as ydl:
        info = ydl.extract_info(track.webpage_url, download=False)
    if not info or not info.get("url"):
        raise ValueError(f"Nie udało się pobrać strumienia audio dla: {track.title}")

    duration_raw = info.get("duration")
    duration = int(duration_raw) if isinstance(duration_raw, (int, float)) and duration_raw > 0 else track.duration
    headers = info.get("http_headers") if isinstance(info.get("http_headers"), dict) else {}
    user_agent = str(headers.get("User-Agent") or track.user_agent or "").strip() or None
    return Track(
        title=str(info.get("title") or track.title).strip(),
        webpage_url=str(info.get("webpage_url") or track.webpage_url),
        requester=track.requester,
        duration=duration,
        uploader=str(info.get("uploader") or info.get("channel") or track.uploader or "").strip() or None,
        thumbnail=str(info.get("thumbnail") or track.thumbnail or "").strip() or None,
        stream_url=str(info["url"]),
        user_agent=user_agent,
    )


async def extract_tracks(query: str, requester: str) -> tuple[list[Track], str | None]:
    return await asyncio.to_thread(_extract_sync, query, requester)


async def resolve_stream(track: Track) -> Track:
    if track.stream_url:
        return track
    return await asyncio.to_thread(_resolve_stream_sync, track)


@dataclass
class GuildMusicState:
    guild_id: int
    queue: deque[Track] = field(default_factory=deque)
    current: Track | None = None
    loop_track: bool = False
    speed: float = DEFAULT_SPEED
    text_channel_id: int | None = None
    idle_task: asyncio.Task[None] | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def enqueue(self, tracks: list[Track]) -> int:
        self.queue.extend(tracks)
        return len(self.queue)

    def next_track(self) -> Track | None:
        if self.loop_track and self.current is not None:
            # Force fresh stream resolution on repeat in case signed URL expired
            return Track(
                title=self.current.title,
                webpage_url=self.current.webpage_url,
                requester=self.current.requester,
                duration=self.current.duration,
                uploader=self.current.uploader,
                thumbnail=self.current.thumbnail,
                stream_url=None,
            )
        if not self.queue:
            self.current = None
            return None
        self.current = self.queue.popleft()
        return self.current

    def clear(self) -> None:
        self.queue.clear()
        self.current = None
        self.loop_track = False

    def cancel_idle_timer(self) -> None:
        if self.idle_task and not self.idle_task.done():
            self.idle_task.cancel()
        self.idle_task = None
