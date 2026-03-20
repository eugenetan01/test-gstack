"""Tests for calendar.py — icalBuddy wrapper and parser."""

import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from cal import (
    Event,
    _parse_attendees,
    _parse_datetime,
    _parse_event_block,
    fetch_tomorrow_events,
    parse_icalbuddy_output,
)


# ---------------------------------------------------------------------------
# parse_icalbuddy_output — core parsing
# ---------------------------------------------------------------------------

def test_parse_valid_single_event():
    output = (
        "EVENT:\n"
        "Team Sync\n"
        "    9:00 AM - 10:00 AM\n"
        "    location: Zoom\n"
        "    attendees: Alice Smith <alice@co.com>, Bob Jones <bob@co.com>\n"
        "    notes: Quarterly review\n"
        "    uid: abc123@google.com\n"
    )
    events = parse_icalbuddy_output(output)
    assert len(events) == 1
    e = events[0]
    assert e.title == "Team Sync"
    assert e.start_time == "9:00 AM"
    assert e.duration == "1 hr"
    assert e.location == "Zoom"
    assert e.attendees == ["Alice Smith", "Bob Jones"]
    assert e.notes == "Quarterly review"
    assert e.uid == "abc123@google.com"


def test_parse_multiple_events():
    output = (
        "EVENT:\nMeeting One\n    9:00 AM - 9:30 AM\n    uid: uid1\n"
        "EVENT:\nMeeting Two\n    2:00 PM - 3:00 PM\n    uid: uid2\n"
    )
    events = parse_icalbuddy_output(output)
    assert len(events) == 2
    assert events[0].title == "Meeting One"
    assert events[1].title == "Meeting Two"


def test_parse_empty_output_returns_empty_list():
    assert parse_icalbuddy_output("") == []
    assert parse_icalbuddy_output("   \n\n  ") == []


def test_deduplication_by_uid():
    """Same uid on two calendars → only one event returned."""
    output = (
        "EVENT:\nSync\n    9:00 AM - 10:00 AM\n    uid: dup-uid\n"
        "EVENT:\nSync\n    9:00 AM - 10:00 AM\n    uid: dup-uid\n"
    )
    events = parse_icalbuddy_output(output)
    assert len(events) == 1


def test_parse_event_with_special_chars_in_title():
    output = "EVENT:\nTeam's Q&A: \"Planning\"\n    9:00 AM - 9:30 AM\n    uid: special1\n"
    events = parse_icalbuddy_output(output)
    assert len(events) == 1
    assert "Q&A" in events[0].title


def test_parse_event_with_unicode_attendee():
    output = (
        "EVENT:\nGlobal Sync\n"
        "    9:00 AM - 10:00 AM\n"
        "    attendees: José García <jose@co.com>, 张伟 <zhang@co.com>\n"
        "    uid: unicode1\n"
    )
    events = parse_icalbuddy_output(output)
    assert len(events) == 1
    assert "José García" in events[0].attendees
    assert "张伟" in events[0].attendees


def test_parse_event_with_multiline_notes():
    """Notes may contain internal newlines — parser should capture what it can."""
    output = (
        "EVENT:\nBig Meeting\n"
        "    9:00 AM - 10:00 AM\n"
        "    notes: Review Q1 results.\n"
        "    uid: multiline1\n"
    )
    events = parse_icalbuddy_output(output)
    assert len(events) == 1
    assert "Q1" in events[0].notes


def test_parse_event_no_attendees():
    """Event with no attendees field → empty list, no crash."""
    output = "EVENT:\nSolo Focus Time\n    9:00 AM - 10:00 AM\n    uid: solo1\n"
    events = parse_icalbuddy_output(output)
    assert len(events) == 1
    assert events[0].attendees == []


# ---------------------------------------------------------------------------
# _parse_datetime
# ---------------------------------------------------------------------------

def test_parse_datetime_standard():
    start, duration = _parse_datetime("2026-03-21, 9:00 AM - 10:00 AM")
    assert start == "9:00 AM"
    assert duration == "1 hr"


def test_parse_datetime_30min():
    start, duration = _parse_datetime("2026-03-21, 2:00 PM - 2:30 PM")
    assert start == "2:00 PM"
    assert duration == "30 min"


def test_parse_datetime_allday():
    start, duration = _parse_datetime("2026-03-21 (all-day)")
    assert start == "all day"
    assert duration == ""


def test_parse_datetime_empty():
    start, duration = _parse_datetime("")
    assert start == "(time unknown)"


# ---------------------------------------------------------------------------
# _parse_attendees
# ---------------------------------------------------------------------------

def test_parse_attendees_with_emails():
    result = _parse_attendees("Alice Smith <alice@co.com>, Bob Jones <bob@co.com>")
    assert result == ["Alice Smith", "Bob Jones"]


def test_parse_attendees_empty():
    assert _parse_attendees("") == []


# ---------------------------------------------------------------------------
# fetch_tomorrow_events — subprocess behaviour
# ---------------------------------------------------------------------------

def test_fetch_exits_if_icalbuddy_missing():
    """FileNotFoundError from subprocess → sys.exit(1)."""
    with patch("cal.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(SystemExit) as exc:
            fetch_tomorrow_events()
        assert exc.value.code == 1


def test_fetch_returns_events_on_success():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "EVENT:\nDaily Standup\n    9:00 AM - 9:15 AM\n    uid: standup1\n"
    mock_result.stderr = ""
    with patch("cal.subprocess.run", return_value=mock_result):
        events = fetch_tomorrow_events()
    assert len(events) == 1
    assert events[0].title == "Daily Standup"
