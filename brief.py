#!/usr/bin/env python3
"""
brief.py — daily calendar briefing entry point.

Usage:
  python brief.py            # fetch events, generate briefs, send notification
  python brief.py --dry-run  # print briefing to stdout, skip notification

Logs every run to ~/.calendar-brief/run.log:
  [2026-03-20 22:00:01] SUCCESS — 4 meetings briefed
  [2026-03-20 22:00:01] FAILED — icalbuddy not installed
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Load .env if present (optional dependency — falls back gracefully)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from cal import fetch_tomorrow_events
from brief_gen import generate_briefs
from notify import send_notification

LOG_FILE = Path.home() / ".calendar-brief" / "run.log"

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily calendar briefing")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print briefing to stdout instead of sending notification",
    )
    args = parser.parse_args()

    try:
        events = fetch_tomorrow_events()
        briefs = generate_briefs(events)

        if args.dry_run:
            _print_briefing(briefs)
        else:
            send_notification(briefs, dry_run=False)
            if briefs:
                _print_briefing(briefs)  # also print to stdout for cron log

        _log_run(success=True, count=len(events))

    except SystemExit:
        _log_run(success=False, message="icalbuddy not installed")
        raise
    except Exception as e:
        _log_run(success=False, message=str(e))
        logging.error("Briefing failed: %s", e)
        sys.exit(1)


def _print_briefing(briefs) -> None:
    """Print full briefing to stdout (used for --dry-run and cron log)."""
    if not briefs:
        print("No meetings tomorrow — clear day!")
        return

    print(f"\n{'='*50}")
    print(f"  TOMORROW'S BRIEFING  ({datetime.now().strftime('%A, %B %-d')})")
    print(f"{'='*50}\n")

    for brief in briefs:
        e = brief.event
        time_str = f"{e.start_time}" + (f" ({e.duration})" if e.duration else "")
        print(f"▸ {e.title}")
        print(f"  {time_str}")
        if e.location:
            print(f"  📍 {e.location}")
        if e.attendees:
            print(f"  👥 {', '.join(e.attendees[:3])}" +
                  (f" +{len(e.attendees)-3} more" if len(e.attendees) > 3 else ""))
        if brief.is_fallback:
            print(f"  ⚠️  (Claude unavailable — showing raw details)")
        else:
            print(f"\n  {brief.text}")
        print()


def _log_run(success: bool, count: int = 0, message: str = "") -> None:
    """Append a timestamped run result to ~/.calendar-brief/run.log."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if success:
            entry = f"[{timestamp}] SUCCESS — {count} meeting{'s' if count != 1 else ''} briefed\n"
        else:
            entry = f"[{timestamp}] FAILED — {message}\n"
        with open(LOG_FILE, "a") as f:
            f.write(entry)
    except Exception as e:
        logging.warning("Could not write run.log: %s", e)


if __name__ == "__main__":
    main()
