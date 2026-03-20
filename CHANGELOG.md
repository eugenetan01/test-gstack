# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0.0] - 2026-03-20

### Added
- **`cal.py`** — icalBuddy wrapper that reads macOS Calendar (supports all synced calendars: Google, iCloud, Exchange). Parses events into structured `Event` dataclass with deduplication by uid. Falls back gracefully when icalBuddy is not installed.
- **`brief_gen.py`** — Claude API wrapper (`claude-haiku-4-5-20251001`) that generates per-meeting 2-3 sentence prep notes. Falls back to raw event summary on API timeout, error, or empty response. No fallback = no notification missed.
- **`notify.py`** — macOS native notification via `osascript`. Sanitizes all text before injection (removes `"`, `\`, newlines). Always uses subprocess list form (never `shell=True`). Supports `--dry-run` mode that prints to stdout.
- **`brief.py`** — Entry point with `--dry-run` flag. Logs every run (success/failure) to `~/.calendar-brief/run.log`.
- **`prompt.txt`** — Claude prompt template using `string.Template`. Asks for purpose, key question, and context in 2-3 sentences.
- **`run.sh`** — Cron wrapper with explicit PATH (`/opt/homebrew/bin` etc.) and optional venv activation.
- **`tests/`** — 40 pytest tests covering all modules: calendar parsing (15), brief generation (9), notifications (11), integration/dry-run (2), and a no-attendees fix (1).
- **`TODOS.md`** — Gmail thread context per meeting captured as P2 TODO for v2.
