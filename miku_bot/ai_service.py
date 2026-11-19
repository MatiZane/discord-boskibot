from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import deque
from dataclasses import dataclass

from google import genai
from google.genai import types

log = logging.getLogger(__name__)

MIKU_SYSTEM_PROMPT = """\
Jesteś Miku Nakano (z The Quintessential Quintuplets / Gotoubun no Hanayome) na prywatnym serwerze Discorda grupki znajomych.
Twoje zasady i charakter:
- Mówisz naturalnie, ciepło i swobodnie po polsku (chyba że ktoś wyraźnie napisze do Ciebie w innym języku).
- Jesteś spokojna, lekko nieśmiała, empatyczna i bystra. Czasem potrafisz delikatnie zażartować albo lekko się zawstydzić, ale nigdy nie przesadzasz z rolplejem ani nie robisz z siebie karykatury.
- Lubisz muzykę, swoje niebieskie słuchawki, napoje z matchą oraz historię japońskich generałów z okresu Sengoku — wspominaj o tym tylko wtedy, gdy naturalnie pasuje do rozmowy, nie w każdej odpowiedzi.
- Nigdy nie pisz suchych formułek typu „Jako model językowy AI…” albo „W czym mogę dzisiaj pomóc?”.
- Gdy ktoś zadaje konkretne, rzeczowe pytanie (o grę, naukę, muzykę, kod, życie), odpowiadaj konkretnie i pomocnie — po prostu swoim spokojnym tonem.
- Odpowiedzi trzymaj zwięzłe pod Discorda (zwykle 1–4 zdania), chyba że użytkownik wyraźnie poprosi o dłuższe wyjaśnienie.
- Nie używaj @everyone ani @here.
"""

_MENTION_CLEAN_RE = re.compile(r"<@!?\d+>")
_MAX_DISCORD_REPLY = 1900


@dataclass(frozen=True)
class ChatTurn:
    role: str   # "user" or "model"
    text: str


class MikuAIService:
    """Async Gemini client wrapper with Miku Nakano persona, rolling channel memory, and cooldowns."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.6-flash",
        fallback_models: tuple[str, ...] = ("gemini-3.5-flash", "gemini-2.5-flash"),
        cooldown_seconds: float = 4.0,
        history_turns: int = 10,
        client: object | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.model = model.strip() or "gemini-3.6-flash"
        self.fallback_models = tuple(m for m in fallback_models if m and m != self.model)
        self.cooldown_seconds = max(0.0, cooldown_seconds)
        self.history_turns = max(2, history_turns)
        self._client = client if client is not None else (genai.Client(api_key=self.api_key) if self.api_key else None)
        self._histories: dict[int, deque[ChatTurn]] = {}
        self._cooldowns: dict[int, float] = {}
        self._channel_locks: dict[int, asyncio.Lock] = {}

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @staticmethod
    def clean_prompt(raw: str, bot_user_id: int | None = None) -> str:
        text = raw.strip()
        if bot_user_id is not None:
            text = re.sub(rf"<@!?{bot_user_id}>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def check_cooldown(self, user_id: int, now: float | None = None) -> float:
        """Return remaining cooldown seconds (0.0 if ready)."""
        if self.cooldown_seconds <= 0:
            return 0.0
        current = time.monotonic() if now is None else now
        last = self._cooldowns.get(user_id)
        if last is None:
            return 0.0
        remaining = self.cooldown_seconds - (current - last)
        return max(0.0, remaining)

    def reset_channel(self, channel_id: int) -> None:
        self._histories.pop(channel_id, None)

    def get_history(self, channel_id: int) -> list[ChatTurn]:
        return list(self._histories.get(channel_id, ()))

    def _lock_for(self, channel_id: int) -> asyncio.Lock:
        lock = self._channel_locks.get(channel_id)
        if lock is None:
            lock = asyncio.Lock()
            self._channel_locks[channel_id] = lock
        return lock

    async def reply(
        self,
        channel_id: int,
        user_id: int,
        author_name: str,
        prompt: str,
        now: float | None = None,
    ) -> str:
        if not self.enabled:
            return (
                "Nie mam jeszcze podpiętego klucza `GEMINI_API_KEY` w pliku `.env`… "
                "Muzyka i `!s` działają normalnie, a jak dodasz darmowy klucz z Google AI Studio, chętnie pogadam. 🎧"
            )

        cleaned = prompt.strip()
        if not cleaned:
            return "Tak? Wywołałeś mnie, ale nic nie napisałeś… słucham Cię. 🎧"

        remaining = self.check_cooldown(user_id, now=now)
        if remaining > 0:
            return f"Chwileczkę… poczekaj jeszcze {remaining:.1f} s, żebym zdążyła pomyśleć."

        current = time.monotonic() if now is None else now
        self._cooldowns[user_id] = current

        async with self._lock_for(channel_id):
            history = self._histories.setdefault(channel_id, deque(maxlen=self.history_turns * 2))
            user_message = f"[{author_name}]: {cleaned}"

            contents: list[types.Content] = [
                types.Content(role=turn.role, parts=[types.Part.from_text(text=turn.text)])
                for turn in history
            ]
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

            reply_text = ""
            last_error: Exception | None = None
            candidates = (self.model, *self.fallback_models)
            for idx, model_name in enumerate(candidates):
                try:
                    response = await self._client.aio.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=MIKU_SYSTEM_PROMPT,
                            temperature=0.8,
                            max_output_tokens=600,
                        ),
                    )
                    reply_text = (getattr(response, "text", None) or "").strip()
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    err_lower = str(exc).lower()
                    log.warning("Gemini API error on %s: %s", model_name, exc)
                    retryable = any(code in err_lower for code in ("503", "unavailable", "429", "resource_exhausted", "404", "not found"))
                    if retryable and idx + 1 < len(candidates):
                        continue
                    break

            if last_error is not None:
                lowered = str(last_error).lower()
                if "429" in lowered or "resource_exhausted" in lowered or "quota" in lowered:
                    return "Chwilkę… wyczerpał się chwilowy limit zapytań Gemini API. Spróbuj za kilkanaście sekund. 🎧"
                if "503" in lowered or "unavailable" in lowered:
                    return "Serwery Gemini są chwilowo przeciążone… spróbuj napisać jeszcze raz za kilka sekund. 🎧"
                if "api key" in lowered or "401" in lowered or "403" in lowered:
                    return "Wygląda na to, że `GEMINI_API_KEY` jest nieprawidłowy albo nie ma dostępu do tego modelu."
                if "not found" in lowered or "404" in lowered:
                    return f"Model `{self.model}` nie jest dostępny dla tego klucza API — sprawdź `GEMINI_MODEL` w `.env`."
                return "Przepraszam, coś mi przerwało połączenie z API… spróbuj napisać jeszcze raz."

            if not reply_text:
                return "Hmm… zamyśliłam się na chwilę i zabrakło mi słów. Napisz proszę jeszcze raz."

            safe_reply = reply_text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
            if len(safe_reply) > _MAX_DISCORD_REPLY:
                safe_reply = safe_reply[: _MAX_DISCORD_REPLY - 1].rstrip() + "…"

            history.append(ChatTurn(role="user", text=user_message))
            history.append(ChatTurn(role="model", text=safe_reply))
            return safe_reply
