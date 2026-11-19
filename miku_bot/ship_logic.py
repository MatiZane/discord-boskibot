from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

SHIP_SALT = "miku-discord-ship-v1"
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ShipResult:
    name_a: str
    name_b: str
    key_a: str
    key_b: str
    percent: int
    ship_name: str
    tier: str
    comment: str
    is_self_ship: bool


def normalize_ship_key(raw: str) -> str:
    """Canonical key for stable, case- and spacing-insensitive ship scores."""
    cleaned = _WHITESPACE_RE.sub(" ", raw.strip()).lower()
    return cleaned.lstrip("@")


def format_display_name(raw: str) -> str:
    """Keep explicit mixed-case nicknames, nicely capitalize all-lowercase plain text."""
    cleaned = _WHITESPACE_RE.sub(" ", raw.strip())
    if not cleaned:
        return "Nieznajomy"
    if cleaned.islower():
        return " ".join(part.capitalize() for part in cleaned.split(" "))
    return cleaned


def build_ship_name(name_a: str, name_b: str) -> str:
    a = _WHITESPACE_RE.sub("", name_a.strip()) or "Mi"
    b = _WHITESPACE_RE.sub("", name_b.strip()) or "Ku"
    left = a[: max(2, (len(a) + 1) // 2)]
    right = b[len(b) // 2 :]
    combined = (left + right).strip()
    if not combined:
        return "MikuShip"
    return combined[0].upper() + combined[1:].lower()


def _tier_and_comment(percent: int, is_self_ship: bool) -> tuple[str, str]:
    if is_self_ship:
        return "high", "Miłość do samego siebie też jest ważna… chyba."
    if percent >= 90:
        return "high", "To już niemal przeznaczenie… aż zrobiło mi się trochę ciepło."
    if percent >= 75:
        return "high", "Naprawdę świetnie do siebie pasujecie. Kibicuję Wam po cichu."
    if percent >= 55:
        return "mid", "Jest tu wyraźna iskra — przy wspólnej playliście wyjdzie jeszcze lepiej."
    if percent >= 35:
        return "mid", "Całkiem spokojna relacja. Dobre słuchawki i matcha potrafią zbliżyć."
    if percent >= 15:
        return "low", "Hmm… na razie raczej znajomi z jednego kanału, ale nigdy nie wiadomo."
    return "low", "Oj… może lepiej zostać przy wspólnym słuchaniu muzyki."


def calculate_ship(
    display_a: str,
    display_b: str,
    key_a: str | None = None,
    key_b: str | None = None,
) -> ShipResult:
    """Compute a permanent, symmetric (A+B == B+A) compatibility percentage (0..100)."""
    nice_a = format_display_name(display_a)
    nice_b = format_display_name(display_b)
    canon_a = normalize_ship_key(key_a if key_a is not None else display_a)
    canon_b = normalize_ship_key(key_b if key_b is not None else display_b)

    is_self = bool(canon_a) and canon_a == canon_b
    if is_self:
        percent = 100
    else:
        ordered = sorted((canon_a, canon_b))
        payload = f"{SHIP_SALT}:{ordered[0]}\0{ordered[1]}".encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        percent = int.from_bytes(digest[:4], "big") % 101

    tier, comment = _tier_and_comment(percent, is_self)
    return ShipResult(
        name_a=nice_a,
        name_b=nice_b,
        key_a=canon_a,
        key_b=canon_b,
        percent=percent,
        ship_name=build_ship_name(nice_a, nice_b),
        tier=tier,
        comment=comment,
        is_self_ship=is_self,
    )
