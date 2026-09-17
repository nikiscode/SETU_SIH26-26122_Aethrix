

<<<<<<< HEAD
# SETU — Planning-to-Execution Bridge

Prototype for **SIH26-26122** — *Intelligent Data Capture & Schedule-Linking
Layer for Infrastructure Project Management*.
Team **Aethrix** (AMITY-2026-4FF6C876) · Theme: Smart Automation (Oil India Limited)

Ingests heterogeneous field progress reports, extracts activity-level actual
start/finish events, links them to the correct L5/L6 activity in the baseline
schedule, and writes actual dates back with a confidence score and a full
audit trail.

---

## Run it

Needs **Python 3.10 or newer** — the code uses `X | None` annotations that
Pydantic resolves at runtime, so 3.9 (which is what stock macOS ships) fails
with a confusing validation error rather than a clear one.

```bash
pip install -r requirements.txt
python -m setu.web                   # the product
```

The baseline can be the sample CSV or a real Primavera **XER** export —
`SETU_PLAN=path/to/project.xer`. A local language model is opt-in:
`SETU_LLM=<ollama model>` (see below for why it is off by default).

It binds loopback only. To reach the field app from a phone on the same
wifi, add `--lan` — that opens it to the network, so it also prints an admin
token that `POST /api/reset` then requires. There is no other
authentication: this is a prototype, not something to point at live project
data.

Then open two windows side by side:

| | |
|---|---|
| **http://127.0.0.1:8000/login** | sign in — start here; the roster explains every role |
| **http://127.0.0.1:8000/agent** | the time agent — say what finished, no forms (supervisor) |
| **http://127.0.0.1:8000/** | planner console — live, updates itself |
| **http://127.0.0.1:8000/audit** | audit trail — trace any figure to its origin (auditor) |
| **http://127.0.0.1:8000/memory** | what actually happened — durations, productivity, causes (PM, head, owner) |
| **http://127.0.0.1:8000/field** | the older plain form, kept for comparison |

Log an entry on the left; it is linked and appears on the console in a few
milliseconds without a refresh. Confirm a queued item on the console and the
schedule updates immediately. Everything persists in `out/setu.db`.

The batch pipeline is still there for the offline evaluation:

```bash
python -m setu.cli demo --fresh      # generate → ingest → link → evaluate → console
open out/planner_console.html
```

Individual stages:

```bash
python -m setu.cli generate   # synthetic L5/L6 plan + 3 input formats + gold labels
python -m setu.cli run        # ingest → extract → link → accrue → write back
python -m setu.cli evaluate   # measured accuracy against the gold set
python -m setu.cli robustness # accuracy under deliberately degraded input
python -m setu.cli agent      # what the time agent's one question buys
python -m setu.cli agent --llm gemma3:270m   # ...and with a local model suggesting
python -m setu.cli memory     # what actually happened: durations, rates, slip
python -m setu.cli console    # planner console HTML
python -m setu.cli trace      # one activity, field text -> schedule, every step named
python -m pytest tests/ -q    # 56 tests
```

No network access, no API keys, nothing hosted. Everything runs locally, which is
the point: a PSU will not send project data to a hosted model.

---

## Measured results

324 L5/L6 activities across 3 areas and 5 disciplines; 334 field entries
across 3 input formats. Cold start, no learned aliases.

| Metric | Result |
|---|---|
| Top-1 link accuracy | **91.3%** |
| Top-3 link accuracy | **99.7%** |
| Auto-committed without a human | **85.7%** of linkable entries (276 of 322) |
| Auto-commit precision | **97.8%** |
| Review queue | 27 entries, proposal correct 88.9% of the time |
| Out-of-plan work correctly flagged | **100%** (12 of 12) |
| Activities updated with actual dates | 176 |

Per input format — note the honest gap:

| Format | Entries | Top-1 | Auto-commit precision |
|---|---|---|---|
| Daily progress report (free text) | 139 | 92.1% | 100.0% |
| Discipline spreadsheet | 112 | 95.5% | 100.0% |
| Supervisor voice / chat | 71 | 83.1% | 89.8% |

Written reports state their area; a supervisor speaking into WhatsApp does
not. That one missing field is the whole difference, and the system routes
lower-confidence voice entries to the planner rather than pretending.

Reproduce with `python -m setu.cli evaluate`; thresholds are fitted by
`sweep.py`, and `calibrate.py` prints the score distributions behind them.

### Does it survive messy input?

One number measured on clean synthetic text invites a fair objection: the
generator and the linker were written by the same hand, so of course they
agree. `python -m setu.cli robustness` answers it with a curve instead. It
degrades a share of the parsed entries — typos, the tag left out, a digit
of the tag mistyped so the entry now cites *someone else's* tag,
romanised Assamese/Hindi in place of the English verb, site shorthand
(`fdn`, `comp.`, `b/f`), shouted case, and missing area / discipline /
quantity — and re-links them. The gold label never moves: a supervisor who
mistypes a tag is still reporting the same work.

| Entries degraded | Top-1 | Top-3 | Auto-commit coverage | Precision |
|---|---|---|---|---|
| 0% | 91.3% | 99.7% | 85.7% | 97.8% |
| 10% | 90.1% | 99.7% | 83.2% | 97.4% |
| 20% | 89.1% | 98.8% | 80.4% | 96.9% |
| 30% | 86.3% | 99.1% | 79.2% | 96.5% |
| 50% | 83.9% | 97.2% | 75.5% | 95.1% |

The shape matters more than any single row. With half the entries degraded,
Top-1 falls 7.5 points but **coverage falls 10.2 while precision falls only
2.8** — degraded entries lose confidence and route to a planner instead of
being committed wrongly, which is exactly what the confidence bands are
for. Out-of-plan recall stays at 100% throughout.

### Does it generalise to wording it has not seen?

The date-split holdout below cannot answer this: every phrasing appears on
both sides of a chronological cut, so it measures unseen *dates*. So each
generated entry now records which of the three phrasings per activity kind
produced it, and `evaluate` also holds back one whole phrasing per kind —
105 events written in 18 of 54 phrasings, none of which the planner is
allowed to confirm.

On that holdout: **Top-1 92.4%, Top-3 99.1%, precision 97.7%** — no worse
than the overall figure, so there is no template-level overfitting. Be
careful how much this is worth, though: all 54 phrasings were written by
the same person who wrote the synonym table, so this shows the vocabulary
generalises across phrasings *of the same origin*. The noise curve above is
the honest probe of words nobody anticipated.

---

## Who it is for

Progress reporting is the evidence trail behind money. A supervisor
reports work; a planner verifies the link; a project manager approves it
into the update; the owner certifies it for payment; an auditor has to
walk any certified figure back to the sentence a named person said on a
named day. That chain is the software:

```
reported  ->  linked  ->  verified  ->  approved  ->  certified
supervisor    (system)    planner      pm            owner
```

Eight roles (supervisor, contractor, planner, PM, head, owner, auditor,
public), each a step or a reader of that chain, all enforced on the server
rather than hidden in a page. Sign in at `/login` — the roster says what
each role can and cannot do, and why.

Two rules that took finding: certification refuses an entry with no
measured quantity, because a certified record without a number cannot
support a payment line; and reading the audit trail is its own privilege,
because guarding it with "is signed in" let the public portal read raw
field text and one person's output over time.

## The time agent

`/agent` is the conversational capture the PS asks for, and it is not a
form. It takes one loose sentence — spoken or typed — fills every slot it
can, and asks **at most one** question, chosen from the linker's own
candidate set by what would actually disambiguate that entry. If the
plausible activities all sit in one area, it does not ask which area.

Measured with `python -m setu.cli agent`:

| | form | agent |
|---|---|---|
| Top-1 accuracy | 91.3% | **92.2%** |
| Auto-commit coverage | 85.7% | **87.3%** |
| Voice channel Top-1 | 83.1% | **87.3%** |

**16 questions across 334 entries — 95% of entries need no follow-up at
all.** A form would have asked every field of every entry. The gain lands
where the gap was: the voice channel, which states no area.

Voice uses the browser's `SpeechRecognition`. Chrome sends audio to Google
unless on-device processing is available, so the page detects which mode
is live and says so on screen — this project claims nothing leaves the
network, and that claim must not quietly stop being true at the microphone.
Entries logged with no signal are kept on the phone and sent when it
returns.

The agent never chooses the activity. The deterministic linker does, which
is why adding a conversation cannot move the precision figures — and why a
local open-weight model could later replace the rule-based slot filling
without touching the ranking.

## Primavera in, Primavera out

The PS names Primavera/MS Project exports as an input. `plan.py` now reads
P6's native **XER** (PROJWBS, TASK, TASKPRED, and UDFs for discipline,
quantity and unit — falling back to the WBS leaf for discipline, which is
how a plain export arrives). The sample project ships as
`data/baseline_schedule.xer` as well as CSV; both load to identical
activities, and the writer is byte-deterministic.

Going back the other way, every run emits `out/p6_update.xlsx` in the
layout **P6 Professional's spreadsheet import** expects — a `TASK` sheet
with internal field names in row 1 and captions in row 2 — so a planner
drags it into *File › Import › Spreadsheet* and the actual dates land on
the activities. In the app, a project manager downloads the same file from
`/memory`, and it carries **only approved-or-certified progress**: what the
chain signed off, never what the model guessed. That is the difference
between "we produce a payload" and "a planner can use this on Monday".
Still not built: a live push over a PMIS API.

## A local LLM — measured, and why it is off by default

The PS asks for an LLM-based time agent. There is one: `agent.py` can hand
each sentence to a local Ollama model to fill the slots the rules leave
empty, validated against the plan's own vocabulary. It **never sees the
plan and never chooses the activity**, so it cannot move the precision
figures however badly it behaves.

And it did behave badly. The model on the development laptop (gemma3,
270M parameters) returned the same area, discipline and action for every
sentence, including sentences that stated a different area in plain words.
Fed to the linker as fact — even after validation, because "Gas
Compression Area" is a valid area — it cost **14.3 points of Top-1** and
collapsed the voice channel from 83.1% to 50.7%.

So the design changed, and this is the rule now: **a model's value is a
suggested answer to the question, never the answer.** It pre-selects a
chip; the linker ignores it until a person taps it. Measured again with
the same model, every accuracy number is identical to rules-only — and the
model's suggestions were right 6 times in 10. Swap in a larger model and
`python -m setu.cli agent --llm <model>` tells you whether to trust its
suggestions, in the same number. It ships disabled (`SETU_LLM` unset)
because that is what the measurement says to do.

## Institutional memory

PS outcome 5(b) asks for a queryable record of what actually happened:
real durations, recurring delay causes, discipline-wise productivity.
`memory.py` computes exactly those three from the entries table — median
planned vs actual duration by activity kind, quantity per working day by
discipline, slippage by area and discipline — and `/memory` shows them.
Planners attach a **delay cause** from a short taxonomy (material,
drawing, access, manpower, weather, permit, rework, predecessor, client,
equipment) when verifying a late entry; those aggregate here instead of
dying as a remark in a DPR column.

A caution on reading the sample numbers: the synthetic generator finishes
multi-entry activities within a few days, so "actual 3d vs planned 8d" is
a property of the data, not a finding about anything. The queries are the
deliverable; the values become meaningful with real entries.

## How the linking works

The hard part is not capture, it is **linking**. A field entry reads
`spool erection completed for process gas line Sec-3`; the plan node reads
`Erect Line 24"-PG-1002 Spools (Sec-3)`. Character overlap is poor and
hundreds of nodes look equally similar. Three stages:

**1 · Candidate generation** — three recall-oriented retrievers, fused with
Reciprocal Rank Fusion:
- exact engineering-tag match (line no., ISO, cable, loop, foundation,
  equipment tag, chainage) after canonicalising notation, so
  `24 inch PG 1002` and `24"-PG-1002` are one key
- BM25 over vocabulary-normalised tokens
- char n-gram TF-IDF cosine, which survives abbreviation

**2 · Constraint re-ranking** — *this is the contribution*. The plan's own
logic prunes the candidate set before similarity decides anything: stated
area, discipline, the planned date window (asymmetric — work slips more
often than it starts early), unit of measure, and whether the reported
quantity still fits inside the planned scope. What separates the right
activity from 400 similar ones is the schedule, not the text.

**3 · Calibrated confidence** — evidence score plus the margin over the
runner-up, bucketed into `auto_commit` / `review` / `unmatched` at
thresholds fitted to a precision floor rather than picked by eye.

Granularity mismatch is handled by **accrual, not 1:1 mapping**: field work
is finer than the WBS, so several entries accrue against one L6 node as
quantity-weighted % complete. Actual start is the first credited entry;
actual finish is when planned quantity is reached or completion is reported.

Nothing is silently dropped. Below the review floor an entry is raised as a
**possible new activity** for the planner — all 12 out-of-plan items in the
sample are caught.

---

## What we tried that did not work

Reported because a prototype that only lists its wins is not evidence.

- **Predecessor-progress penalty.** Intuitive, and measurably harmful: it
  fires on every activity that opens a chain, before anything downstream is
  credited. Cost ~4 points of Top-1. Removed.
- **Fuzzy alias matching.** Token-set similarity over short site phrases
  collides constantly (`welding completed Sec-2` vs `Sec-4`), stamping high
  confidence on wrong activities — ~15 points of auto-commit precision.
  Now only exact, unambiguous, constraint-checked phrasings bypass the ranker.
- **Alias learning as a confidence boost.** Bought +12% coverage for −16
  points of precision, because it lifts every activity of the same *kind*
  equally: more certainty, no more evidence. Demoted to a tie-breaker that
  changes the pick without changing the claimed confidence.
- **The learning flywheel, honestly.** On held-out later entries, 16 planner
  confirmations moved Top-1 by **+0.0%** and coverage by **+0.0%**. Measured
  again on a split that cannot leak — hold back one whole phrasing per
  activity kind, let the planner confirm only the others — 14 confirmations
  moved Top-1 by **+0.0%** and coverage by **+0.0%** as well. Two
  independent splits, no movement. We do not claim a flywheel. Exact-phrase
  reuse helps with repeated DPR boilerplate and nothing more; making
  corrections generalise is open work.

Two bugs the test suite caught, both of which had been silently inflating
results: the inch-normaliser eating the `IN` out of `LP-IN-0789`, and BM25
scores never being normalised into [0,1] (negative IDF made the divisor tiny,
so one signal swamped the rest and pinned confidence at a clipped 1.0).

---

## Layout

```
setu/
  models.py     PlanActivity, ProgressEvent, LinkResult, confidence bands
  tags.py       engineering-tag grammar, vocabulary normalisation
  synth.py      synthetic project generator + gold labels
  formats.py    three writers, three parsers (DPR text, xlsx, voice log)
  plan.py       baseline I/O: CSV and Primavera XER; P6 spreadsheet update
  linker.py     retrieval → constraint re-rank → calibrated confidence
  accrual.py    quantity-weighted % complete, actual start/finish
  pipeline.py   end-to-end run + outputs
  noise.py      adversarial degradation of field text, for the curve
  agent.py      the time agent: slot filling, one question, gated local LLM
  roles.py      eight roles and the five-stage approval chain
  memory.py     durations, productivity, slippage, delay causes
  evaluate.py   gold-set scoring, date and wording holdouts
  report.py     planner console (self-contained HTML)
data/inputs/    the three sample input files
out/            actual_progress.csv, p6_writeback.json, p6_update.xlsx,
                review_queue.csv, audit_trail.csv, planner_console.html,
                robustness.csv, agent_eval.csv
```

## What is real and what is scaffolded

**Real:** ingestion of three genuinely different field formats and a
Primavera XER baseline; tag grammar and vocabulary normalisation; hybrid
retrieval; constraint re-ranking; confidence calibration; accrual; the
time agent (conversation, browser voice, one question, gated local LLM);
eight roles on a five-stage approval chain with named attribution; review
queue with per-item reasons; audit trail and auditor query view;
institutional memory (durations, productivity, slippage, delay causes);
a P6-importable schedule update; the planner console with a planned-vs-
actual timeline; the robustness curve and wording holdout; 56 tests.

**Scaffolded, deliberately:** write-back is a file P6 imports rather than
a live push over a PMIS API — the file is the form most sites actually
use, and a push needs a client-side endpoint plus a change-control
decision about who may write to a contractual baseline. Voice is the
browser's speech recogniser rather than Whisper; the PS says
production-grade ASR is not required, and the page states whether audio
stays on the device. The local LLM is present but off by default, because
measuring it said so (see above); a larger model is a config line.

**Not built:** OCR for scanned diaries (PS excuses it); an MS Project XML
reader (XER only); the WhatsApp transport itself (the agent is the same
conversation without it); cross-project portfolio — one process serves one
project, so the head's view is single-project; dedicated screens for the
contractor and owner roles beyond their enforced APIs.

---

## Where this sits against what already exists

Three groups of tools touch this problem, and none of them close it.

**Vision-based progress tracking** — OpenSpace (360° walkthrough cameras),
Buildots (hard-hat-mounted cameras), Doxel (robots and drones with LiDAR).
These measure progress directly and accurately, but they need capital
hardware, a capture routine, and a BIM model to compare against. They suit
vertical building work far better than a linear oil-and-gas plant, and none
of them help with the reports a project is *already* producing.

**Field reporting apps** — Procore, Fieldwire, Raken and similar. These do
capture daily progress, but they solve the problem by moving it: the
supervisor picks the activity from a list. That works when the workforce
will adopt a new structured app, and fails exactly where this PS lives —
multi-contractor sites where reporting arrives as free text, spreadsheets
and WhatsApp in whatever form each contractor already uses.

**Schedule analytics** — SmartPM, nPlan, ALICE and Primavera's own
analytics. These consume schedule updates to forecast and analyse. They are
downstream of the gap: they need someone to have already produced a clean,
current, linked update, which is the thing that does not exist.

SETU sits in the space between: it takes the unstructured reporting a
project already generates, with no new hardware and no change to how
supervisors work, and produces the linked, current, structured update the
analytics layer needs. The claim is not that it measures progress better
than a LiDAR scan — it plainly does not. The claim is that it is the only
one of these that costs nothing to adopt, because it consumes what the
project already writes.

---

## A note on reproducing these numbers

Top-1 accuracy, auto-commit coverage and precision are stable across
machines. Top-3 varies by about a third of a point (99.4–99.7%) depending on
the numpy / scikit-learn build, because a handful of candidates at ranks 2–3
tie on score and get ordered differently. The figures quoted here and on the
deck are from the demo laptop; if your run differs by a decimal, that is why.
=======
# Sih-hackothon-
>>>>>>> da02754452d293e1edc98369a081a98e33d580eb
