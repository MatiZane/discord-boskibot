from __future__ import annotations

from types import SimpleNamespace

import pytest

from miku_bot.ai_service import MikuAIService


class _FakeModels:
    def __init__(self, reply_text: str = "Cześć… chętnie posłucham z Tobą muzyki. 🎧", error: Exception | None = None) -> None:
        self.reply_text = reply_text
        self.error = error
        self.calls: list[dict] = []

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(text=self.reply_text)


class _FakeClient:
    def __init__(self, models: _FakeModels) -> None:
        self.aio = SimpleNamespace(models=models)


@pytest.mark.asyncio
async def test_ai_disabled_without_api_key() -> None:
    service = MikuAIService(api_key="")
    assert service.enabled is False
    answer = await service.reply(channel_id=1, user_id=10, author_name="Mati", prompt="Hej!")
    assert "GEMINI_API_KEY" in answer


@pytest.mark.asyncio
async def test_ai_tracks_history_sanitizes_mentions_and_enforces_cooldown() -> None:
    models = _FakeModels(reply_text="Hej @everyone, posłuchajmy czegoś spokojnego.")
    service = MikuAIService(api_key="test-key", cooldown_seconds=5.0, history_turns=2, client=_FakeClient(models))

    ans1 = await service.reply(channel_id=42, user_id=7, author_name="Mati", prompt="Cześć Miku!", now=100.0)
    assert "@everyone" not in ans1
    assert "@\u200beveryone" in ans1
    assert len(service.get_history(42)) == 2

    # Within cooldown -> blocked without calling Gemini
    ans_cd = await service.reply(channel_id=42, user_id=7, author_name="Mati", prompt="Szybko!", now=101.5)
    assert "poczekaj" in ans_cd.lower()
    assert len(models.calls) == 1

    # After cooldown -> includes previous channel history
    await service.reply(channel_id=42, user_id=7, author_name="Mati", prompt="Co lubisz pić?", now=106.0)
    assert len(models.calls) == 2
    assert len(models.calls[1]["contents"]) == 3  # 2 history turns + 1 new user turn

    service.reset_channel(42)
    assert service.get_history(42) == []


@pytest.mark.asyncio
async def test_ai_handles_rate_limit_gracefully() -> None:
    models = _FakeModels(error=RuntimeError("429 RESOURCE_EXHAUSTED"))
    service = MikuAIService(api_key="test-key", fallback_models=(), cooldown_seconds=0.0, client=_FakeClient(models))
    ans = await service.reply(channel_id=1, user_id=1, author_name="Mati", prompt="Halo?")
    assert "limit" in ans.lower()


@pytest.mark.asyncio
async def test_ai_falls_back_to_backup_model_on_503() -> None:
    class _FallbackModels:
        def __init__(self) -> None:
            self.models_tried: list[str] = []

        async def generate_content(self, **kwargs):
            self.models_tried.append(kwargs["model"])
            if kwargs["model"] == "gemini-3.6-flash":
                raise RuntimeError("503 UNAVAILABLE")
            return SimpleNamespace(text="Udało się odpowiedzieć z modelu zapasowego.")

    fake = _FallbackModels()
    service = MikuAIService(
        api_key="test-key",
        model="gemini-3.6-flash",
        fallback_models=("gemini-2.5-flash",),
        cooldown_seconds=0.0,
        client=_FakeClient(fake),
    )
    ans = await service.reply(channel_id=5, user_id=2, author_name="Mati", prompt="Test")
    assert "zapasowego" in ans
    assert fake.models_tried == ["gemini-3.6-flash", "gemini-2.5-flash"]


def test_clean_prompt_strips_bot_mention() -> None:
    assert MikuAIService.clean_prompt("<@!123456>  hej Miku  ", bot_user_id=123456) == "hej Miku"
    assert MikuAIService.clean_prompt("<@123456>", bot_user_id=123456) == ""
