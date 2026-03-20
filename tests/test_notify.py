"""Tests for notify.py — notification formatting and osascript safety."""

import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from cal import Event
from brief_gen import Brief
from notify import (
    MAX_BODY_CHARS,
    _sanitize,
    format_notification,
    send_notification,
)


def _make_brief(title="Test Meeting", start_time="9:00 AM", **kwargs) -> Brief:
    event = Event(
        uid="uid1",
        title=title,
        start_time=start_time,
        duration="1 hr",
        **kwargs,
    )
    return Brief(event=event, text="Prep note.")


# ---------------------------------------------------------------------------
# format_notification
# ---------------------------------------------------------------------------

def test_format_zero_briefs():
    title, body = format_notification([])
    assert "clear day" in body.lower() or "no meetings" in body.lower()


def test_format_single_brief():
    title, body = format_notification([_make_brief()])
    assert "1 meeting" in title
    assert "Test Meeting" in body


def test_format_multiple_briefs():
    briefs = [
        _make_brief("Sync", "9:00 AM"),
        _make_brief("Design Review", "11:00 AM"),
        _make_brief("1:1", "2:00 PM"),
    ]
    title, body = format_notification(briefs)
    assert "3 meetings" in title
    assert "Sync" in body
    assert "Design Review" in body


def test_format_truncates_long_body():
    """Body must not exceed MAX_BODY_CHARS."""
    briefs = [_make_brief(f"Meeting {'x' * 50} {i}", "9:00 AM") for i in range(5)]
    _, body = format_notification(briefs)
    assert len(body) <= MAX_BODY_CHARS


def test_format_shows_overflow_count():
    """More than MAX_TITLE_BRIEFS meetings → '+N more' shown."""
    briefs = [_make_brief(f"Meeting {i}", "9:00 AM") for i in range(6)]
    _, body = format_notification(briefs)
    assert "more" in body


# ---------------------------------------------------------------------------
# _sanitize — osascript injection prevention
# ---------------------------------------------------------------------------

def test_sanitize_removes_double_quotes():
    assert '"' not in _sanitize('Say "hello"')


def test_sanitize_removes_backslashes():
    assert "\\" not in _sanitize("path\\to\\file")


def test_sanitize_replaces_newlines():
    result = _sanitize("line1\nline2")
    assert "\n" not in result


def test_sanitize_plain_text_unchanged():
    text = "Team sync at 9am"
    assert _sanitize(text) == text


def test_sanitize_apostrophe_preserved():
    """Single quotes are safe in osascript double-quoted strings."""
    result = _sanitize("Team's meeting")
    assert "Team's meeting" == result


# ---------------------------------------------------------------------------
# send_notification — subprocess behaviour
# ---------------------------------------------------------------------------

def test_send_notification_dry_run_does_not_call_osascript(capsys):
    briefs = [_make_brief()]
    with patch("notify.subprocess.run") as mock_run:
        send_notification(briefs, dry_run=True)
        mock_run.assert_not_called()
    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


def test_send_notification_uses_subprocess_list_form():
    """osascript must be called as a list, not shell=True."""
    briefs = [_make_brief()]
    with patch("notify.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        send_notification(briefs, dry_run=False)
        call_args = mock_run.call_args
        # First positional arg must be a list starting with 'osascript'
        cmd = call_args[0][0]
        assert isinstance(cmd, list)
        assert cmd[0] == "osascript"
        # Must NOT use shell=True
        assert not call_args[1].get("shell", False)


def test_send_notification_title_with_quotes_does_not_crash():
    """Event title with quotes must not break osascript call."""
    brief = _make_brief(title='Team\'s "Important" Meeting')
    with patch("notify.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        send_notification([brief], dry_run=False)
        # Should have called osascript without raising
        mock_run.assert_called_once()
