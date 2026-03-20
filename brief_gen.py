"""
brief_gen.py — generate per-meeting prep notes via Claude API.

Pipeline:
  list[Event]
      │
      ▼ for each event (serial)
  Template(prompt.txt).safe_substitute(event fields)
      │
      ▼
  anthropic.messages.create(prompt)
      │ success               │ APIError / Timeout / empty
      ▼                       ▼
  Brief(event, text)    Brief(event, raw_summary(event))
                              │ log warning
      ▼
  list[Brief]
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from string import Template

import anthropic

from cal import Event

logger = logging.getLogger(__name__)

PROMPT_FILE = Path(__file__).parent / "prompt.txt"
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 300


@dataclass
class Brief:
    event: Event
    text: str
    is_fallback: bool = False


def generate_briefs(events: list[Event]) -> list[Brief]:
    """Generate a prep brief for each event. Falls back to raw summary on API failure."""
    if not events:
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — using raw summaries for all events")
        return [Brief(event=e, text=e.raw_summary(), is_fallback=True) for e in events]

    client = anthropic.Anthropic(api_key=api_key)
    prompt_template = _load_prompt_template()

    briefs = []
    for event in events:
        brief = _generate_one(client, prompt_template, event)
        briefs.append(brief)
    return briefs


def _generate_one(client: anthropic.Anthropic, template: Template, event: Event) -> Brief:
    """Generate a single brief, falling back to raw summary on any error."""
    prompt = _render_prompt(template, event)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip() if response.content else ""
        if not text:
            raise ValueError("Empty response from Claude")
        return Brief(event=event, text=text)
    except anthropic.APITimeoutError as e:
        logger.warning("Claude API timeout for '%s': %s", event.title, e)
    except anthropic.APIError as e:
        logger.warning("Claude API error for '%s': %s", event.title, e)
    except Exception as e:
        logger.warning("Unexpected error generating brief for '%s': %s", event.title, e)

    return Brief(event=event, text=event.raw_summary(), is_fallback=True)


def _render_prompt(template: Template, event: Event) -> str:
    """Render the prompt template with event fields."""
    duration_line = f" ({event.duration})" if event.duration else ""
    location_line = event.location if event.location else "(no location)"
    attendees_line = ", ".join(event.attendees) if event.attendees else "(no attendees)"
    notes_line = event.notes[:500] if event.notes else "(no notes)"

    return template.safe_substitute(
        title=event.title,
        start_time=event.start_time,
        duration_line=duration_line,
        location_line=location_line,
        attendees_line=attendees_line,
        notes_line=notes_line,
    )


def _load_prompt_template() -> Template:
    """Load prompt.txt as a string.Template."""
    try:
        return Template(PROMPT_FILE.read_text())
    except FileNotFoundError:
        logger.error("prompt.txt not found at %s", PROMPT_FILE)
        # Minimal inline fallback
        return Template(
            "Write a 2-sentence prep note for this meeting: $title at $start_time."
        )
