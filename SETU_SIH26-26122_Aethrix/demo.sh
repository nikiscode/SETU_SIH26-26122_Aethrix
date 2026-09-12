#!/usr/bin/env bash
# SETU screening demo — paced walkthrough of input → run → output.
#
#   ./demo.sh          step through with Enter between stages
#   DEMO_AUTO=1 ./demo.sh   run straight through (for rehearsal timing)
#
# Nothing here is staged: every command is the real pipeline.

set -u
cd "$(dirname "$0")"
# Prefer the project venv: the system python3 on macOS is 3.9, which cannot
# run this code (X | None annotations resolved at runtime by Pydantic).
# Override with PY=... if your interpreter lives somewhere else.
if [ -z "${PY:-}" ]; then
  if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
fi
if ! "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
  echo "  $PY is too old (need Python 3.10+). Try: PY=.venv/bin/python $0"
  exit 1
fi

B=$'\033[1m'; D=$'\033[2m'; C=$'\033[36m'; Y=$'\033[33m'; X=$'\033[0m'

pause() { [ "${DEMO_AUTO:-}" = "1" ] || { printf "\n%s" "$D   [Enter]$X"; read -r _; }; }
stage() { clear; printf "\n%s\n%s\n\n" "$B$1$X" "$D$2$X"; }

# ── 0 ────────────────────────────────────────────────────────────────
stage "SETU — Planning-to-Execution Bridge" \
      "SIH26-26122 · Team Aethrix · everything below runs offline, right now"
cat <<'EOT'
  The plan lives in Primavera, in L5/L6 activities.
  Actual progress comes back as daily reports, contractor spreadsheets
  and WhatsApp messages — none of which mention an activity ID.

  Three inputs. One plan. Nothing connecting them.
EOT
pause

# ── 1 · INPUT ────────────────────────────────────────────────────────
stage "1 · INPUT — a free-text daily progress report" \
      "data/inputs/dpr_daily_report.txt"
$PY - <<'EOF'
# show the richest report block, not whichever happens to be first
import re
blocks = re.split(r"={40,}\n(?=DAILY)", open("data/inputs/dpr_daily_report.txt").read())
best = max(blocks, key=lambda b: b.count("  - "))
print("=" * 64)
print(best.rstrip())
EOF
pause

stage "1 · INPUT — a contractor's discipline register" \
      "data/inputs/piping_civil_register.xlsx"
$PY - <<'EOF'
import pandas as pd
d = pd.read_excel("data/inputs/piping_civil_register.xlsx")
print(d[["Date","Area","Discipline","Description of Work Done","Qty","UOM"]]
      .head(7).to_string(index=False))
print(f"\n  ... {len(d)} rows")
EOF
pause

stage "1 · INPUT — supervisor voice / chat messages" \
      "data/inputs/voice_timeagent_log.txt  ·  no area, no discipline, no IDs"
head -6 data/inputs/voice_timeagent_log.txt
pause

# ── 2 · THE PLAN ─────────────────────────────────────────────────────
stage "2 · THE PLAN — what all of that has to be matched against" \
      "data/baseline_schedule.csv"
$PY - <<'EOF'
import pandas as pd
d = pd.read_csv("data/baseline_schedule.csv")
print(d[["activity_id","description","discipline",
         "planned_start","planned_finish"]].head(6).to_string(index=False))
print(f"\n  {len(d)} L5/L6 activities across "
      f"{d.discipline.nunique()} disciplines.")
print("  Not one field entry above names any of them.")
EOF
pause

# ── 3 · RUN ──────────────────────────────────────────────────────────
stage "3 · RUN" "python -m setu.cli run --fresh"
time $PY -m setu.cli run --fresh
pause

# ── 4 · OUTPUT: one activity, end to end ─────────────────────────────
stage "4 · OUTPUT — following one activity from field text to schedule" \
      "python -m setu.cli trace"
$PY -m setu.cli trace
pause

# ── 5 · OUTPUT: the planner console ──────────────────────────────────
stage "5 · OUTPUT — the planner console" "out/planner_console.html"
$PY -m setu.cli console
printf "  Opening in your browser...\n"
( command -v open >/dev/null && open out/planner_console.html ) 2>/dev/null \
  || ( command -v xdg-open >/dev/null && xdg-open out/planner_console.html ) 2>/dev/null \
  || printf "  %sOpen out/planner_console.html manually.%s\n" "$Y" "$X"
pause

# ── 6 · PROOF ────────────────────────────────────────────────────────
stage "6 · PROOF — measured, not claimed" \
      "every synthetic field entry carries the activity it really belongs to"
$PY -m setu.cli evaluate 2>/dev/null | sed -n '1,16p'
pause

stage "6 · PROOF — the test suite" "python -m pytest tests/ -q"
$PY -m pytest tests/ -q
printf "\n%s  Outputs on disk:%s\n" "$B" "$X"
ls -1 out/ | sed 's/^/    /'
printf "\n"
