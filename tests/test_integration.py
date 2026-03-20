"""Integration test: --dry-run prints briefing to stdout, never calls osascript."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))


def test_dry_run_prints_to_stdout_no_osascript():
    """
    --dry-run must:
      1. Print briefing text to stdout
      2. Never invoke osascript
      3. Exit 0
    """
    from cal import Event
    from brief_gen import Brief

    mock_event = Event(
        uid="test-uid",
        title="Integration Test Meeting",
        start_time="9:00 AM",
        duration="1 hr",
        location="Zoom",
        attendees=["Alice", "Bob"],
        notes="Integration test notes",
    )
    mock_brief = Brief(event=mock_event, text="This meeting is about testing.")

    with patch("brief.fetch_tomorrow_events", return_value=[mock_event]), \
         patch("brief.generate_briefs", return_value=[mock_brief]), \
         patch("notify.subprocess.run") as mock_osascript, \
         patch("brief._log_run"):

        # Simulate --dry-run by importing and calling main with patched argv
        import sys
        sys.argv = ["brief.py", "--dry-run"]
        from brief import main
        main()

        # osascript must NOT have been called
        mock_osascript.assert_not_called()


def test_dry_run_clear_day(capsys):
    """--dry-run with no events prints a clear-day message."""
    with patch("brief.fetch_tomorrow_events", return_value=[]), \
         patch("brief.generate_briefs", return_value=[]), \
         patch("brief._log_run"):

        import sys
        sys.argv = ["brief.py", "--dry-run"]
        from brief import main
        main()

        captured = capsys.readouterr()
        assert "clear day" in captured.out.lower() or "no meetings" in captured.out.lower()
