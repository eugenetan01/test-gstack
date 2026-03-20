# calendar-briefing

Daily meeting prep, delivered as a macOS notification at 10pm.

Reads your Mac Calendar (Google, iCloud, Exchange — whatever's synced), generates a 2-3 sentence prep note per meeting using Claude, and delivers it as a native macOS notification.

## How it works

```
Mac Calendar (icalBuddy)
       │
       ▼
  cal.py — parse events, deduplicate by uid
       │
       ▼
  brief_gen.py — Claude Haiku API per meeting
       │         (falls back to raw summary if API unavailable)
       ▼
  notify.py — osascript notification
               (or stdout with --dry-run)
```

## Setup

```bash
# 1. Install icalBuddy
brew install icalbuddy

# 2. Clone and configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Install dependencies
python3 -m venv .venv
.venv/bin/pip install anthropic

# 4. Test it (--dry-run prints to stdout, never fires notification)
.venv/bin/python brief.py --dry-run
```

## Cron (runs 10pm every night)

```bash
crontab -e
# Add:
0 22 * * * /path/to/calendar-briefing/run.sh
```

Logs every run to `~/.calendar-brief/run.log`.

## Running tests

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest -v
```

40 tests across calendar parsing, Claude API fallbacks, osascript safety, and dry-run integration.

## Requirements

- macOS (for icalBuddy and osascript)
- Python 3.10+
- `brew install icalbuddy`
- `ANTHROPIC_API_KEY` in `.env`

## v2 roadmap

See `TODOS.md` — Gmail thread context per meeting is next.
