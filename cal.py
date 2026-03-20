"""
calendar.py — fetch tomorrow's events via icalBuddy.

Data flow:
  subprocess(['icalbuddy', '-b', 'EVENT:', ...])
      │ stdout (each event prefixed with 'EVENT:')
      ▼
  parse_icalbuddy_output(stdout: str) -> list[Event]
      │ splits on 'EVENT:' separator
      │ extracts fields with per-field fallbacks
      │ deduplicates by Event.uid
      ▼
  list[Event(uid, title, start_time, duration,
             location, attendees, notes, url)]

Shadow paths:
  FileNotFoundError  → print install hint, sys.exit(1)
  empty stdout       → return []
  parse error/field  → use '' fallback, log warning
"""

import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

ICALBUDDY_SEPARATOR = "EVENT:"


@dataclass
class Event:
    uid: str
    title: str
    start_time: str
    duration: str
    location: str = ""
    attendees: list = field(default_factory=list)
    notes: str = ""
    url: str = ""
    # v2 fields — empty in v1, reserved for Gmail/Drive context
    email_threads: list = field(default_factory=list)
    drive_docs: list = field(default_factory=list)

    def raw_summary(self) -> str:
        """Fallback text used when Claude API is unavailable."""
        parts = [f"{self.title} at {self.start_time} ({self.duration})"]
        if self.location:
            parts.append(f"Location: {self.location}")
        if self.attendees:
            shown = self.attendees[:3]
            parts.append(f"Attendees: {', '.join(shown)}")
        if self.notes:
            parts.append(f"Notes: {self.notes[:200]}")
        return "\n".join(parts)


def fetch_tomorrow_events() -> list[Event]:
    """Run icalBuddy and return tomorrow's events, deduplicated."""
    try:
        result = subprocess.run(
            [
                "icalbuddy",
                "-b", f"{ICALBUDDY_SEPARATOR}\n",  # unique event prefix
                "-nc",                              # no calendar names
                "-iep", "title,datetime,location,attendees,notes,url,uid",
                "eventsFrom:tomorrow", "to:tomorrow",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except FileNotFoundError:
        print("Error: icalbuddy is not installed.", file=sys.stderr)
        print("Fix:   brew install icalbuddy", file=sys.stderr)
        sys.exit(1)

    if result.stderr:
        logger.warning("icalbuddy stderr: %s", result.stderr.strip())

    return parse_icalbuddy_output(result.stdout)


def parse_icalbuddy_output(output: str) -> list[Event]:
    """
    Parse raw icalBuddy stdout into a deduplicated list of Events.
    Each event block starts with ICALBUDDY_SEPARATOR on its own line.
    """
    events = []
    seen_uids: set[str] = set()

    blocks = [b.strip() for b in output.split(ICALBUDDY_SEPARATOR) if b.strip()]

    for block in blocks:
        event = _parse_event_block(block)
        if event is None:
            continue
        if event.uid in seen_uids:
            logger.debug("Skipping duplicate event uid=%s title=%s", event.uid, event.title)
            continue
        seen_uids.add(event.uid)
        events.append(event)

    return events


def _parse_event_block(block: str) -> "Event | None":
    """
    Parse a single icalBuddy event block into an Event.
    Returns None if the block has no usable title.

    Example block (after stripping the separator):
        Team Sync
            date: 2026-03-21, 9:00 AM - 10:00 AM
            location: Zoom
            attendees: Alice <a@co.com>, Bob <b@co.com>
            notes: Weekly review
            url: https://zoom.us/j/123
            uid: abc123@google.com
    """
    lines = block.splitlines()
    if not lines:
        return None

    # First non-empty line is the title
    title = ""
    prop_lines = []
    for i, line in enumerate(lines):
        if not title and line.strip():
            title = line.strip()
        elif title:
            prop_lines.append(line)

    if not title:
        return None

    # Parse property lines (indented with whitespace + label: value)
    props: dict[str, str] = {}
    for line in prop_lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Match "label: value" or bare value (datetime has no label)
        match = re.match(r"^([a-zA-Z]+):\s*(.*)$", stripped)
        if match:
            props[match.group(1).lower()] = match.group(2).strip()
        elif not props.get("datetime"):
            # First unmatched line is likely the datetime
            props["datetime"] = stripped

    start_time, duration = _parse_datetime(props.get("datetime", ""))
    attendees = _parse_attendees(props.get("attendees", ""))
    uid = props.get("uid", "") or _generate_fallback_uid(title, start_time)

    return Event(
        uid=uid,
        title=title,
        start_time=start_time,
        duration=duration,
        location=props.get("location", ""),
        attendees=attendees,
        notes=props.get("notes", ""),
        url=props.get("url", ""),
    )


def _parse_datetime(raw: str) -> tuple[str, str]:
    """
    Extract a human-readable start time and duration from icalBuddy datetime string.

    Handles formats like:
      "2026-03-21, 9:00 AM - 10:00 AM"
      "2026-03-21 (Saturday), 9:00 AM - 10:00 AM"
      "2026-03-21 (all-day)"
    """
    if not raw:
        return ("(time unknown)", "")

    if "all-day" in raw.lower():
        return ("all day", "")

    # Extract time range: "9:00 AM - 10:00 AM"
    time_match = re.search(r"(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(\d{1,2}:\d{2}\s*[AP]M)", raw, re.IGNORECASE)
    if time_match:
        start = time_match.group(1).strip()
        end = time_match.group(2).strip()
        duration = _calc_duration(start, end)
        return (start, duration)

    # Fallback: return whatever we have
    return (raw[:50], "")


def _calc_duration(start: str, end: str) -> str:
    """Return human-readable duration between two time strings like '9:00 AM' and '10:30 AM'."""
    try:
        from datetime import datetime as dt
        fmt = "%I:%M %p"
        s = dt.strptime(start.upper(), fmt)
        e = dt.strptime(end.upper(), fmt)
        mins = int((e - s).total_seconds() / 60)
        if mins <= 0:
            return ""
        if mins % 60 == 0:
            hours = mins // 60
            return f"{hours} hr" if hours == 1 else f"{hours} hrs"
        hours, rem = divmod(mins, 60)
        if hours == 0:
            return f"{rem} min"
        return f"{hours} hr {rem} min"
    except Exception:
        return ""


def _parse_attendees(raw: str) -> list[str]:
    """
    Parse attendees string into a list of display names.
    Handles: "Alice Smith <alice@co.com>, Bob Jones <bob@co.com>"
    """
    if not raw:
        return []
    attendees = []
    for part in raw.split(","):
        part = part.strip()
        # Extract display name from "Name <email>" or use raw
        name_match = re.match(r"^(.+?)\s*<[^>]+>$", part)
        if name_match:
            attendees.append(name_match.group(1).strip())
        elif part:
            attendees.append(part)
    return attendees


def _generate_fallback_uid(title: str, start_time: str) -> str:
    """Generate a deterministic uid for events missing one."""
    return f"{title.lower().replace(' ', '-')}-{start_time.replace(':', '').replace(' ', '')}"
