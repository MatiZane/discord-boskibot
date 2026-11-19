from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class BotConfig:
    discord_token: str
    gemini_api_key: str
    gemini_model: str
    gemini_fallback_models: tuple[str, ...]
    command_prefix: str
    guild_ids: tuple[int, ...]
    ship_emoji_high: str
    ship_emoji_mid: str
    ship_emoji_low: str
    ai_cooldown_seconds: float
    ai_history_turns: int
    voice_idle_seconds: int
    ffmpeg_executable: str

    @property
    def ai_enabled(self) -> bool:
        return bool(self.gemini_api_key.strip())


def resolve_ffmpeg(configured: str = "") -> str:
    """Resolve FFmpeg executable: explicit .env path -> system PATH -> bundled imageio-ffmpeg."""
    if configured:
        candidate = Path(configured)
        if candidate.is_file():
            return str(candidate)
        found = shutil.which(configured)
        if found:
            return found

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _parse_int_list(raw: str | None) -> tuple[int, ...]:
    if not raw or not raw.strip():
        return ()
    result: list[int] = []
    for part in raw.split(","):
        cleaned = part.strip()
        if not cleaned:
            continue
        try:
            result.append(int(cleaned))
        except ValueError:
            continue
    return tuple(dict.fromkeys(result))


def _parse_float(raw: str | None, default: float, minimum: float = 0.0) -> float:
    if not raw or not raw.strip():
        return default
    try:
        return max(minimum, float(raw.strip()))
    except ValueError:
        return default


def _parse_int(raw: str | None, default: int, minimum: int = 1) -> int:
    if not raw or not raw.strip():
        return default
    try:
        return max(minimum, int(raw.strip()))
    except ValueError:
        return default


def load_config(env_path: str | Path | None = None) -> BotConfig:
    if env_path is not None:
        load_dotenv(dotenv_path=env_path, override=False)
    else:
        load_dotenv(override=False)

    discord_token = os.getenv("DISCORD_TOKEN", "").strip()
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip() or "gemini-3.6-flash"
    fallback_raw = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash,gemini-2.5-flash")
    gemini_fallback_models = tuple(
        dict.fromkeys(m.strip() for m in fallback_raw.split(",") if m.strip() and m.strip() != gemini_model)
    )
    command_prefix = os.getenv("COMMAND_PREFIX", "!").strip() or "!"

    return BotConfig(
        discord_token=discord_token,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
        gemini_fallback_models=gemini_fallback_models,
        command_prefix=command_prefix,
        guild_ids=_parse_int_list(os.getenv("GUILD_ID")),
        ship_emoji_high=os.getenv("SHIP_EMOJI_HIGH", "").strip(),
        ship_emoji_mid=os.getenv("SHIP_EMOJI_MID", "").strip(),
        ship_emoji_low=os.getenv("SHIP_EMOJI_LOW", "").strip(),
        ai_cooldown_seconds=_parse_float(os.getenv("AI_COOLDOWN_SECONDS"), 4.0, minimum=0.0),
        ai_history_turns=_parse_int(os.getenv("AI_HISTORY_TURNS"), 10, minimum=2),
        voice_idle_seconds=_parse_int(os.getenv("VOICE_IDLE_SECONDS"), 300, minimum=30),
        ffmpeg_executable=resolve_ffmpeg(os.getenv("FFMPEG_PATH", "").strip()),
    )
