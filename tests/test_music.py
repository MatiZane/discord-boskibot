from __future__ import annotations

import pytest

from miku_bot.music_engine import (
    GuildMusicState,
    Track,
    build_ffmpeg_options,
    clamp_speed,
    format_duration,
    format_speed,
    normalize_query,
)


def test_normalize_query_supports_urls_shorts_and_plain_search() -> None:
    shorts = "https://www.youtube.com/shorts/7oxr4MDFiNg"
    assert normalize_query(shorts) == shorts
    assert normalize_query("gotoubun no kimochi") == "ytsearch1:gotoubun no kimochi"
    with pytest.raises(ValueError):
        normalize_query("   ")


def test_speed_clamping_formatting_and_ffmpeg_filters() -> None:
    assert clamp_speed(float("nan")) == 1.0
    assert clamp_speed(0.1) == 0.5
    assert clamp_speed(5.0) == 2.0
    assert clamp_speed(1.25) == 1.25

    assert format_speed(1.0) == "1×"
    assert format_speed(1.25) == "1,25×"
    assert format_speed(1.5) == "1,5×"

    before_1, opts_1 = build_ffmpeg_options(1.0)
    assert "-reconnect 1" in before_1
    assert opts_1 == "-vn"

    before_ua, opts_fast = build_ffmpeg_options(1.5, user_agent="Mozilla/5.0 Test")
    assert "-user_agent" in before_ua
    assert opts_fast == "-vn -af atempo=1.50"


def test_duration_and_guild_queue_loop_behavior() -> None:
    assert format_duration(0) == "na żywo / nieznany"
    assert format_duration(125) == "2:05"
    assert format_duration(3661) == "1:01:01"

    state = GuildMusicState(guild_id=1)
    t1 = Track(title="First", webpage_url="https://youtu.be/aaa", requester="Mati", stream_url="https://stream/1")
    t2 = Track(title="Second", webpage_url="https://youtu.be/bbb", requester="Mati")
    assert state.enqueue([t1, t2]) == 2

    first = state.next_track()
    assert first is not None and first.title == "First"

    state.loop_track = True
    repeated = state.next_track()
    assert repeated is not None and repeated.title == "First"
    assert repeated.stream_url is None  # Forces fresh URL resolution on loop

    state.loop_track = False
    second = state.next_track()
    assert second is not None and second.title == "Second"
    assert state.next_track() is None


def test_davey_version_compatible_with_discord_py() -> None:
    import davey
    import discord

    discord_minor = tuple(int(p) for p in discord.__version__.split(".")[:2])
    davey_minor = tuple(int(p) for p in davey.__version__.split(".")[:2])
    if discord_minor < (2, 8):
        assert davey_minor < (0, 2), (
            f"davey {davey.__version__} breaks DAVE voice encryption on discord.py {discord.__version__} "
            "(can_encrypt stays False); pin davey>=0.1.6,<0.2.0."
        )
