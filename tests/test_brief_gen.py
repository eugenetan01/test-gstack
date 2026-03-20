"""Tests for brief_gen.py — Claude API wrapper and fallback logic."""

import sys
from string import Template
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from cal import Event
from brief_gen import Brief, _generate_one, _render_prompt, generate_briefs


def _make_event(**kwargs) -> Event:
    defaults = dict(
        uid="test-uid",
        title="Test Meeting",
        start_time="9:00 AM",
        duration="1 hr",
        location="Zoom",
        attendees=["Alice", "Bob"],
        notes="Review Q1 results",
        url="https://zoom.us/j/123",
    )
    defaults.update(kwargs)
    return Event(**defaults)


def _make_template() -> Template:
    return Template("Meeting: $title at $start_time$duration_line. Location: $location_line.")


# ---------------------------------------------------------------------------
# generate_briefs — happy path
# ---------------------------------------------------------------------------

def test_generate_briefs_happy_path():
    events = [_make_event(), _make_event(uid="uid2", title="Second Meeting")]
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Prep note here.")]

    with patch("brief_gen.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = mock_response
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            briefs = generate_briefs(events)

    assert len(briefs) == 2
    assert all(b.text == "Prep note here." for b in briefs)
    assert all(not b.is_fallback for b in briefs)


def test_generate_briefs_empty_events():
    assert generate_briefs([]) == []


def test_generate_briefs_no_api_key_uses_raw_summary():
    events = [_make_event()]
    with patch.dict("os.environ", {}, clear=True):
        # Ensure no key in env
        import os
        os.environ.pop("ANTHROPIC_API_KEY", None)
        briefs = generate_briefs(events)
    assert len(briefs) == 1
    assert briefs[0].is_fallback
    assert "Test Meeting" in briefs[0].text


# ---------------------------------------------------------------------------
# _generate_one — API failure fallbacks
# ---------------------------------------------------------------------------

def test_api_timeout_falls_back_to_raw_summary():
    import anthropic
    client = MagicMock()
    client.messages.create.side_effect = anthropic.APITimeoutError(request=MagicMock())
    event = _make_event()
    brief = _generate_one(client, _make_template(), event)
    assert brief.is_fallback
    assert "Test Meeting" in brief.text


def test_api_error_falls_back_to_raw_summary():
    import anthropic
    client = MagicMock()
    client.messages.create.side_effect = anthropic.APIError(
        message="server error", request=MagicMock(), body=None
    )
    event = _make_event()
    brief = _generate_one(client, _make_template(), event)
    assert brief.is_fallback


def test_empty_api_response_falls_back():
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = []
    client.messages.create.return_value = mock_response
    event = _make_event()
    brief = _generate_one(client, _make_template(), event)
    assert brief.is_fallback


# ---------------------------------------------------------------------------
# _render_prompt — template rendering
# ---------------------------------------------------------------------------

def test_render_prompt_with_full_event():
    t = Template("$title at $start_time$duration_line loc=$location_line att=$attendees_line notes=$notes_line")
    event = _make_event()
    result = _render_prompt(t, event)
    assert "Test Meeting" in result
    assert "9:00 AM" in result
    assert "Zoom" in result
    assert "Alice" in result
    assert "Q1 results" in result


def test_render_prompt_no_attendees():
    """Event with no attendees renders without crashing."""
    t = Template("$title at $start_time$duration_line. Attendees: $attendees_line.")
    event = _make_event(attendees=[])
    result = _render_prompt(t, event)
    assert "(no attendees)" in result


def test_render_prompt_no_location():
    t = _make_template()
    event = _make_event(location="")
    result = _render_prompt(t, event)
    assert "(no location)" in result
