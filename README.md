# Miku Discord Bot 🎧

Lokalny bot na prywatny serwer Discorda z klimatem **Miku Nakano**:
- **Muzyka z YouTube** (zwykłe linki, **YouTube Shorts**, playlisty do 50 utworów, wyszukiwanie po nazwie, kolejka, pętla, przyciski sterujące oraz regulacja prędkości `0,5×–2×` z naturalną tonacją).
- **Karty zgodności (`!s` / `/ship`)** — stały, symetryczny wynik dla pary nicków lub `@wzmianek` (kolejność osób nie zmienia wyniku) oraz generowana w locie karta graficzna PNG z avatarami i komentarzem Miku.
- **Mini-AI Miku Nakano** — rozmowy przez darmowe **Google Gemini API** po `@wzmiankowaniu` bota, po odpowiedzi (`Reply`) na jego wiadomość lub przez `!miku` / `/miku`, z pamięcią ostatnich wiadomości na kanale, krótkim cooldownem i automatycznym zapasem modeli Flash (`gemini-3.6-flash` → `gemini-3.5-flash` → `gemini-2.5-flash`).

Wszystkie główne komendy działają **hybrydowo** — zarówno przez klasyczny prefiks `!`, jak i przez slash-komendy `/`.

---

## Komendy

| Działanie | Prefiks `!` | Slash `/` |
| --- | --- | --- |
| Karta zgodności (ship) | `!s @nick1 nick2` lub `!s nick` | `/ship osoba1 [osoba2]` |
| Odtwórz muzykę (link / Shorts / tytuł) | `!p <zapytanie>` | `/play <zapytanie>` |
| Kolejka utworów | `!q` | `/queue` |
| Pomiń / pauza / wznów | `!skip`, `!pause`, `!resume` | `/skip`, `/pause`, `/resume` |
| Pętla utworu | `!loop` | `/loop` |
| Prędkość odtwarzania (`0.5–2.0`) | `!speed 1.25` | `/speed 1.25` |
| Zatrzymaj i wyjdź z kanału | `!stop` / `!leave` | `/stop` |
| Zapytaj Miku (AI) | `!miku <pytanie>` lub `@Miku ...` / Reply | `/miku <pytanie>` |
| Wyczyść pamięć AI na kanale | `!mikureset` | `/miku_reset` |

---

## Konfiguracja krok po kroku (pierwsze uruchomienie)

### 1. Discord Developer Portal (Token bota + Intents)
1. Wejdź na https://discord.com/developers/applications i wybierz swoją aplikację (np. **Sigemka** — możesz tam zmienić jej nazwę i avatar na Miku) albo utwórz nową (**New Application**).
2. W zakładce **Bot**:
   - Kliknij **Reset Token** i skopiuj token (wkleisz go do `.env` jako `DISCORD_TOKEN`).
   - Włącz **Privileged Gateway Intents**:
     - **Message Content Intent** (wymagane dla komend `!s`, `!p`, `!miku` oraz `@wzmianek`)
     - **Server Members Intent** (rozpoznawanie nicków i avatarów serwera w `!s`)
3. Jeśli to nowa aplikacja: w **OAuth2 → URL Generator** zaznacz `bot` + `applications.commands`, a w uprawnieniach `Send Messages`, `Attach Files`, `Embed Links`, `Read Message History`, `Connect`, `Speak`, `Use External Emojis` i otwórz wygenerowany link, aby dodać bota na serwer.

### 2. Darmowy klucz Gemini API (Google AI Studio)
1. Wejdź na https://aistudio.google.com/apikey i kliknij **Create API key** (na Free Tierze bez podpinania karty).
2. Skopiuj klucz i wklej do `.env` jako `GEMINI_API_KEY`.
3. Model ustawia zmienna `GEMINI_MODEL` (domyślnie `gemini-3.6-flash` z automatycznym fallbackiem `GEMINI_FALLBACK_MODELS`). Możesz ją zmienić na dowolny model dostępny na Twoim kluczu.

*(Jeśli na razie zostawisz `GEMINI_API_KEY` puste, muzyka i `!s` nadal będą działać w 100% normalnie).*

### 3. Uruchomienie lokalne (Windows)
1. Skopiuj `.env.example` do `.env` i uzupełnij `DISCORD_TOKEN` oraz `GEMINI_API_KEY` (opcjonalnie `GUILD_ID`, żeby komendy `/` pojawiły się na Twoim serwerze od razu).
2. Odpal jednym poleceniem:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run.ps1
   ```
   Skrypt sam tworzy `.venv`, instaluje zależności (w tym `yt-dlp` i wbudowane `FFmpeg` przez `imageio-ffmpeg`) i uruchamia bota.

---

## Testy

```powershell
.\.venv\Scripts\pytest.exe -v
```

Plik `.env` znajduje się w `.gitignore` — tokeny i klucze API nigdy nie trafiają do repozytorium Git.
