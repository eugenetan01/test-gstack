"""
notify.py — send a macOS native notification via osascript.

Safety: event titles are sanitized before injection into AppleScript.
subprocess list form used throughout — no shell=True.
"""

import logging
import subprocess

from brief_gen import Brief

logger = logging.getLogger(__name__)

MAX_BODY_CHARS = 200
MAX_TITLE_BRIEFS = 4  # number of meeting titles shown in notification body


def send_notification(briefs: list[Brief], dry_run: bool = False) -> None:
    """Send a macOS notification summarising tomorrow's meetings."""
    title, body = format_notification(briefs)

    if dry_run:
        print("--- DRY RUN: would send notification ---")
        print(f"Title: {title}")
        print(f"Body:  {body}")
        print("----------------------------------------")
        return

    _osascript_notify(title, body)


def format_notification(briefs: list[Brief]) -> tuple[str, str]:
    """Return (notification_title, notification_body) for the given briefs."""
    n = len(briefs)

    if n == 0:
        return ("Daily Briefing", "Clear day tomorrow — no meetings.")

    meeting_word = "meeting" if n == 1 else "meetings"
    title = f"Daily Briefing — {n} {meeting_word} tomorrow"

    # Body: "9:00 AM: Sync · 11:00 AM: Design review · ..."
    snippets = []
    for brief in briefs[:MAX_TITLE_BRIEFS]:
        e = brief.event
        label = f"{e.start_time}: {e.title}" if e.start_time else e.title
        snippets.append(label)

    body = " · ".join(snippets)
    if n > MAX_TITLE_BRIEFS:
        body += f" · +{n - MAX_TITLE_BRIEFS} more"

    # Truncate to macOS notification limit
    if len(body) > MAX_BODY_CHARS:
        body = body[: MAX_BODY_CHARS - 1] + "…"

    return (title, body)


def _sanitize(text: str) -> str:
    """
    Escape text for safe embedding in an AppleScript string literal.
    Removes characters that could break or inject AppleScript.
    """
    # Replace backslashes first, then quotes
    text = text.replace("\\", "")
    text = text.replace('"', "'")
    text = text.replace("\n", " ").replace("\r", " ")
    return text


def _osascript_notify(title: str, body: str) -> None:
    """Fire a macOS native notification using osascript subprocess list form."""
    safe_title = _sanitize(title)
    safe_body = _sanitize(body)

    script = (
        f'display notification "{safe_body}" '
        f'with title "{safe_title}" '
        f'sound name "Default"'
    )

    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.CalledProcessError as e:
        logger.error("osascript failed (exit %d): %s", e.returncode, e.stderr.strip())
    except subprocess.TimeoutExpired:
        logger.error("osascript timed out")
    except FileNotFoundError:
        logger.error("osascript not found — are you on macOS?")
