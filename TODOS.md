# TODOS

## P2 — Gmail context per meeting (v2)

**What:** Add Gmail thread surfacing per meeting — search Gmail for threads mentioning
attendees + event title from the past 30 days, inject as context into the Claude prompt.

**Why:** The current v1 brief is generated from calendar metadata only. Gmail context
enables the "whoa" moment: "Last time you discussed Q1 budget — Sarah mentioned a freeze.
Has it been lifted?" That's the original Approach B from the design doc and the real
prep quality improvement.

**Pros:** Dramatically better prep notes. Closes the gap between "calendar summary" and
"I know what's going on before I walk in."

**Cons:** Requires Google OAuth (Gmail read scope), credential storage, and a relevance
filter to avoid noise. Adds ~2 OAuth scopes and a token refresh flow that v1 deliberately
avoided.

**Context:** v1 uses icalBuddy (no OAuth) + Claude + osascript. Gmail context was
deferred to validate the v1 format first — make sure you actually read the briefing
daily before adding complexity. Start here once v1 is running reliably for 1-2 weeks.

**Effort:** M human / S with CC
**Priority:** P2
**Depends on:** v1 shipping and being used daily
