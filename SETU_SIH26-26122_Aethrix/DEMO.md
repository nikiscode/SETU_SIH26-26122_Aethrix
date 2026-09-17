
  # SETU — screening demo runbook

Everything below runs on one laptop, offline. Total demo time: ~4 minutes.

---

## Before you leave home (5 minutes, once)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m setu.cli demo --fresh
open out/planner_console.html
```

**Use `.venv/bin/python` for every command in this file.** The system
`python3` on macOS is 3.9 and cannot run this code at all — it fails with a
confusing Pydantic error, which is not what you want to debug in the room.
Needs 3.10+.

If that prints numbers and opens a dashboard, you are ready. Do this the
night before, not in the room — the only thing that can fail is `pip
install`, and it needs network.

**Then run it once more with the wifi off.** That is the actual demo
condition, and it proves the "nothing leaves the network" claim on slide 3.

Have two windows open before you present: a terminal in `~/Hack-2026/setu`,
and `out/planner_console.html` in a browser tab.

---

## The live demo — two windows (strongest opening)

```bash
.venv/bin/python -m setu.web
```

Put two windows side by side on the projector:

- **left** — http://127.0.0.1:8000/field (the supervisor's app)
- **right** — http://127.0.0.1:8000/ (the planner's console)

**For the phone, you need `--lan`:**

```bash
.venv/bin/python -m setu.web --lan
```

The server binds loopback only by default, so a phone cannot reach it
otherwise. `--lan` opens it to the wifi and prints the address to use plus
an admin token for the reset endpoint. A phone in your hand sells this far
better than a browser tab, so it is worth the extra flag — but test it on
the venue wifi before you present, because guest networks routinely block
device-to-device traffic.

The field app has six tap-to-fill example entries, in this order, and each
one exists to make a different point:

| # | Tap | What happens | What to say |
|---|---|---|---|
| 1 | spools erected on line 12"-CW-1001 | auto-links, ~5 ms | *"Different words from the plan. It found the activity from the line number."* |
| 2 | terminations completed CBL-EL-0455 | auto-links | *"Different discipline, same story."* |
| 3 | loop checking completed LP-IN-0779 | auto-links, conf 1.00 | *"Exact tag match — it is certain, and says so."* |
| 4 | concrete pouring completed for foundation at Sec-1 | auto-links | *"No tag at all here. It linked on discipline, area, section and the date window."* |
| 5 | cable termination done at Sec-1 | **goes to review** | *"No tag, no area. It won't guess — it proposes and asks."* Then confirm it on the console. |
| 6 | temporary shoring installed at north access road | **flagged as new** | *"Not in the plan at all. It doesn't force-fit; it raises it for the next revision."* |

Watch the console after each tap: the feed slides the entry in, the tiles
move, and the plan-vs-actual table gains a row — no refresh, ever.

**The moment to slow down for is #5.** Confirm it on the console and say:
*"That correction is now stored. The planner taught it, and it did not have
to touch the schedule to do it."*

Upload also works live — drag `data/inputs/dpr_daily_report.txt` at
`/api/docs` if someone asks whether it handles the existing paperwork; all
334 sample entries ingest in one call.

---

### When they ask about Primavera

```bash
head -12 data/baseline_schedule.xer
SETU_PLAN=data/baseline_schedule.xer .venv/bin/python -m setu.cli run --fresh
```

*"That is a real P6 export format, not a CSV standing in for one. And the
update goes back the same way"* — open `out/p6_update.xlsx`: *"this is the
layout P6 imports directly. A planner drags it in on Monday."*

### When they ask about the LLM

```bash
.venv/bin/python -m setu.cli agent --llm gemma3:270m
```

Lead with the failure, because it is the strongest thing you have: *"We
wired in a local model and measured it. Fed to the linker as fact it cost
14 points of accuracy. So it can only suggest — pre-select a chip — and the
linker ignores it until a person taps. Same model, no accuracy change. A
bigger model is a config line and the same command tells you if it earns
its place."* Nobody else in the room will have measured their LLM.

### The head's screen

Sign in as **D. Sharma** → `/memory`. *"This is what leaves with the people
when a project closes: how long rebar fixing actually takes, cable laid
per day, where it slips and why. Every number comes from linked, verified
entries."*

## The batch script (fallback, or if you prefer terminal)

```bash
./demo.sh
```

Six stages, Enter between each, so you control the pace and never type a
command in front of the panel. It shows the three inputs, the plan, the run,
one activity traced end to end, the console, and the proof. Nothing is
staged — every stage runs the real pipeline.

`DEMO_AUTO=1 ./demo.sh` runs straight through, for rehearsing your timing.

What to *say* over each stage is below.

---

## The demo, in order

### 1 · Show the mess going in (30 sec)

```bash
head -20 data/inputs/dpr_daily_report.txt
```

Say: *"This is a daily progress report. Free text, written by a supervisor.
No activity IDs anywhere."*

```bash
open data/inputs/piping_civil_register.xlsx     # or: head -5 on the csv
head -5 data/inputs/voice_timeagent_log.txt
```

Say: *"Same project, two more formats — a contractor's spreadsheet and
WhatsApp voice messages. Three different shapes, none of them linked to the
plan."*

Then show what they have to be matched against:

```bash
head -3 data/baseline_schedule.csv
```

Say: *"And this is the plan — 324 L5/L6 activities. Nothing in the field
reports names them."* **This is the moment the problem lands. Don't rush it.**

### 2 · Run it (30 sec)

```bash
.venv/bin/python -m setu.cli run --fresh
```

Takes under two seconds. Read the output aloud — it breaks down per format,
and shows how many went to auto-commit, review, and flagged-as-new.

### 3a · Trace one activity (45 sec) — *the moment it lands*

```bash
.venv/bin/python -m setu.cli trace
```

Picks the worst-slipping activity and shows its whole life: the planned
dates, then every field entry that fed it — the raw sentence, which file and
line it came from, what tag was extracted, what confidence it linked at —
then the actual dates written back.

Say: *"Two entries. One typed into a spreadsheet by one man, one spoken into
WhatsApp by another, five weeks apart, neither mentioning an activity ID.
Together they say this cable termination finished 33 days late."*

Then, pointing at the second entry: *"That one had no engineering tag at all.
It linked on the schedule constraints — discipline, area, date window, and
the remaining quantity on that activity."*

To trace a specific one: `.venv/bin/python -m setu.cli trace OIL-A1-ELE-L6-0057`

### 3b · Show the console (60 sec)

Switch to the browser tab, reload `out/planner_console.html`.

Walk it top to bottom:

- **Tiles** — 334 entries in, 176 activities updated with real actual dates.
- **"Where every field entry went"** — the green/amber/red bar. Say: *"Nothing
  is discarded. What we're unsure about goes to a planner. What has no plan
  node at all gets raised as a possible new activity."*
- **By input format** — the honest table. Say: *"Written reports link at 92
  and 95 percent with 100 percent precision. Voice is 83. The difference is
  one field: a written report states its area, a man talking into WhatsApp
  doesn't. The system knows it's weaker there and routes those to review
  instead of guessing."*
- **Plan vs actual** — scroll to a row with a big red slippage number. Say:
  *"This is the output. That activity finished 33 days late and nobody had
  to reconcile a spreadsheet to find out."*
- **Review queue** — point at the "why it stopped here" column. Say: *"Every
  decision explains itself. A planner confirms or corrects; nothing is
  silently committed."*

### 4 · Prove the numbers (45 sec)

```bash
.venv/bin/python -m setu.cli evaluate
.venv/bin/python -m pytest tests/ -q
```

Say: *"Every field entry in our synthetic data carries the activity it really
belongs to, so accuracy is measured, not claimed. 91.3% Top-1, 97.8%
precision on what we commit without a human, and 100% of out-of-plan work
correctly flagged. 56 tests."*

`evaluate` also prints two holdouts. Point at the second one: *"A date split
leaks, because every phrasing appears on both sides of the cut. So we also
hold back one whole phrasing per activity kind — 105 entries the planner is
never allowed to confirm. 92.4% there, no worse than overall."*

If anyone presses on synthetic data — and someone should — that is the cue
for the robustness curve:

```bash
.venv/bin/python -m setu.cli robustness
```

---

## If they ask

**"Is this real or hard-coded?"**
Do **not** say "regenerate and you get a new random project" — the generator
is seeded (7 and 11), so `cli generate` reproduces the same project byte for
byte. That is deliberate and it is the better answer: *"It is deterministic
on purpose. Same input, same output — that is what makes 97.8% precision a
number you can check rather than a number we remember."*

To actually show it is not hardcoded, do one of these:

```bash
.venv/bin/python -m setu.cli robustness
```

*"We degrade our own input — typos, tags left out, a mistyped tag digit so
the entry cites someone else's tag, Assamese and Hindi in place of the
English verb — and report how fast we fall. Half the entries degraded costs
7.5 points of accuracy and 2.8 of precision."* Nothing hardcoded survives
that. Or open `setu/linker.py` and walk the three-stage matcher.

**"Why not just fuzzy string matching?"**
Show `data/baseline_schedule.csv` — hundreds of activities on the same line
in the same section. Text alone cannot separate `Erect Line 24"-PG-1002` from
`Hydrotest Line 24"-PG-1002`. The schedule can: discipline, date window,
remaining quantity, stated area. That's `_constraints()` in `linker.py`.

**"What if it gets one wrong?"**
Only high-confidence links auto-commit — measured 97.8% precision, and the
threshold is one number in `models.py` that a planner can dial. Everything
else queues. `out/audit_trail.csv` has every raw input, extracted tag,
candidate set and decision, so any commit can be traced and reversed.

**"How much is actually built?"**
Be straight: ingestion, tag grammar, hybrid retrieval, constraint re-ranking,
confidence calibration, accrual, review queue, audit trail, the approval
chain with named attribution, the time agent, institutional memory, the
Primavera XER reader and the P6-importable update are all real. Voice is
the browser's recogniser, not Whisper, and says on screen whether audio
stays on the device. A local LLM is wired in but off by default — because
we measured it (say that; it lands). Not built: OCR, an MS Project XML
reader, a live PMIS API push, the WhatsApp transport, and multi-project.

**"Does it learn from corrections?"**
Don't oversell this. Say: *"Exact repeated phrasings, yes. We tested whether
planner corrections generalise to unseen entries and measured plus zero
percent, so we're not claiming a flywheel — it's in our README as open work."*
Volunteering a negative result is the single most credible thing you can do
in that room.

---

## If the laptop dies

`SIH26-26122_Aethrix_IdeaPPT.pdf` — slide 6 carries a screenshot of the
console with the same figures. `out/*.csv` can be opened on any machine.
Keep a copy on a phone.

---

## Split for 3 presenters

- **P1 — the problem.** Slides 1–2 and demo step 1. Owns "why linking, not
  capture, is the hard part."
- **P2 — the system.** Slide 3 and demo steps 2–3. Drives the laptop.
- **P3 — evidence and limits.** Demo step 4, slides 4–6, and all Q&A on what
  isn't built. Must know the "what we tried that did not work" section cold.
