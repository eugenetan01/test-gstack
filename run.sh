#!/bin/bash
# run.sh — cron wrapper for brief.py
#
# Add to crontab:
#   0 22 * * * /path/to/run.sh   # 10pm nightly
#   0 6  * * * /path/to/run.sh   # 6am same-day catch
#
# Logs to ~/.calendar-brief/run.log

# Explicit PATH — cron does not inherit the login shell PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Activate virtualenv if present
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
  source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Load .env if present
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

cd "$SCRIPT_DIR"
exec python3 brief.py "$@"
