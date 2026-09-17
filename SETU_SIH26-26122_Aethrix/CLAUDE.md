
# SETU — Planning-to-Execution Bridge

Smart India Hackathon 2026, problem statement **SIH26-26122** (Intelligent
Data Capture & Schedule-Linking Layer for Infrastructure Project
Management). Theme: Smart Automation, Oil India Limited. Team **Aethrix**
(AMITY-2026-4FF6C876).

Takes the field progress reporting a project already produces — free-text
daily reports, contractor spreadsheets, WhatsApp voice messages — and links
each entry to the correct L5/L6 activity in the baseline schedule, writing
actual dates back with a confidence score and a full audit trail.

## Run

```bash
pip install -r requirements.txt
python -m setu.web        # live app: / = planner console, /field = supervisor
                          # loopback only; --lan to expose (mints a reset token)
python -m setu.cli demo --fresh   # batch pipeline + offline evaluation
python -m setu.cli robustness     # accuracy vs deliberately degraded input
python -m setu.cli agent          # what the time agent's one question buys
python -m setu.cli agent --llm M  # ...with a local Ollama model suggesting
python -m setu.cli memory         # durations, productivity, slippage, causes
python -m setu.cli trace          # one activity: raw text -> +33 days late
python -m pytest tests/ -q        # 56 tests
```

No API key, no network, no model weights required. Verified running with
the network removed. `SETU_PLAN` may point at a P6 `.xer` instead of the
CSV; `SETU_LLM=<ollama model>` opts into a local model (off by default —
see below). Needs Python 3.10+ (`X | None` annotations are resolved at runtime
by Pydantic; 3.9 fails obscurely). `SETU_DB` overrides the SQLite path,
`SETU_ADMIN_TOKEN` guards `POST /api/reset`.

## Measured (cold start, no learned aliases)

324 L5/L6 activities, 334 field entries across 3 formats.

| | |
|---|---|
| Top-1 link accuracy | 91.3% |
| Top-3 | 99.4–99.7% (varies ±0.3pt by numpy/sklearn build, tie-breaking) |
| Auto-committed without a human | 85.7% of linkable entries (276 of 322) |
| Auto-commit precision | 97.8% |
| Review queue | 27 entries, proposal correct 88.9% |
| Out-of-plan work flagged | 100% (12 of 12) |

Per format — the gap is the honest part of the story: DPR 92.1% Top-1 /
100% precision, spreadsheet 95.5% / 100%, voice 83.1% / 89.8%. Written
reports state their area; a supervisor dictating into WhatsApp does not.
That one missing field is the whole difference, and the system routes the
weaker channel to review rather than guessing.

Reproduce: `python -m setu.cli evaluate`. Thresholds fitted by
`tools/sweep.py`; `tools/calibrate.py` prints the score distributions.

**Robustness** (`cli robustness`, `noise.py`). Degrading a share of parsed
entries — typos, dropped tag, mistyped tag digit (so the entry cites
someone else's tag), romanised Assamese/Hindi verbs, site shorthand,
shouted case, missing area/discipline/quantity — with the gold label held
fixed:

| degraded | 0% | 10% | 20% | 30% | 50% |
|---|---|---|---|---|---|
| Top-1 | 91.3% | 90.1% | 89.1% | 86.3% | 83.9% |
| coverage | 85.7% | 83.2% | 80.4% | 79.2% | 75.5% |
| precision | 97.8% | 97.4% | 96.9% | 96.5% | 95.1% |

At 50% degraded, Top-1 falls 7.5 points but coverage falls 10.2 while
precision falls only 2.8 — the bands do their job, shedding coverage rather
than committing wrongly. Out-of-plan recall stays 100% at every level. Cite
the *shape*, not one row.

**Wording holdout.** Each generated entry records which of the three
phrasings per activity kind produced it (`template_id`, gold file only —
never in the linker's input). `evaluate` holds back one whole phrasing per
kind: 105 events, 18 of 54 phrasings, unconfirmable by the planner. Result
Top-1 92.4%, Top-3 99.1%, precision 97.7% — no template-level overfitting.
Do not oversell it: all 54 phrasings share one author with the synonym
table, so it shows generalisation across phrasings of the same origin. The
noise curve is the honest probe of unanticipated words.

## Who uses it (`roles.py`)

Progress reporting is the evidence trail behind money, not a reporting
exercise. Roles are steps in that chain, not view filters:

```
reported  ->  linked  ->  verified  ->  approved   ->  certified
supervisor    (system)    planner      pm             owner
```

Eight roles: supervisor, contractor, planner, pm, head, owner, auditor,
public. Every transition records **who** and **when**. Enforcement is
server-side (`require()`, `require_audit_view()`), not template-level.

Rules worth not breaking:

- **Org is a confidentiality boundary, area is not.** An entry with no org
  recorded is hidden from a scoped role (it might be a competitor's); an
  entry with no area stays visible. Asymmetric on purpose.
- **Certification requires a measured quantity.** It is the step that
  turns progress into money owed; a certified entry with no number is a
  record worth nothing. Found by walking the chain by hand.
- **Reading the trail is its own privilege.** Guarding the audit endpoints
  with "is signed in" let the public portal read raw field text and one
  person's output over time. `require_audit_view` exists for that.
- **Attribution comes from the session, never the request body**, or a
  client can file progress under someone else's name.

Migrations are ordered and recorded in `schema_version` (`db.py`). Before
that, the first schema change on a live database had no upgrade path.

## Institutional memory (`memory.py`)

The PS names three things that get lost when a project closes: real
durations, recurring delay causes, discipline-wise productivity. Those
three are what `build_memory()` computes, from the same entries table
everything else derives from — so it cannot drift from the evidence. Read
`/memory` (pm, head, owner, planner, auditor; gated because productivity
is commercially sensitive). Delay causes come from a short taxonomy the
planner picks at verification; junk keys are dropped, not stored.

The synthetic generator finishes multi-entry activities within days, so the
sample's "actual 3d vs planned 8d" is a data artefact. Do not present it
as a finding.

## The time agent (`agent.py`)

PS outcome 2. Not a form: one loose sentence in, every slot it can fill
filled, and **at most one** question — chosen from the linker's own
candidate set by what would actually disambiguate *this* entry. If the
candidates all agree on area, asking for area removes nothing, so it does
not ask.

Measured (`cli agent`): **16 questions across 334 entries — 95% need no
follow-up at all.** Voice channel Top-1 83.1% -> 87.3% (+4.2pt), overall
+0.9pt, coverage +1.6pt. The simulated supervisor answers the area
correctly; that is the assumption inside the number.

The agent never picks the activity — the deterministic linker does. That
is what stops a conversational front end from moving the precision
figures, and why a local LLM can later slot into `understand()` without
putting anything generative in the ranking path.

`max_questions` is enforced **server-side**. Without it the endpoint asks
until every slot is full, which is a form again delivered one question at
a time — and it would invalidate the 16-question figure.

## Architecture

`linker.py` is the core and the only file with real subtlety. Three stages:

1. **Candidate generation** — exact engineering-tag match (line no., ISO,
   cable, loop, foundation, equipment, chainage, after canonicalising
   notation so `24 inch PG 1002` == `24"-PG-1002`), BM25 over
   vocabulary-normalised tokens, and char n-gram TF-IDF cosine. Fused with
   Reciprocal Rank Fusion.
2. **Constraint re-ranking** — *the contribution*. The plan's own logic
   prunes before similarity decides: stated section, stated area,
   discipline, planned date window (asymmetric — work slips more often than
   it starts early), unit of measure, remaining planned quantity. What
   separates the right activity from 300 similar ones is the schedule, not
   the text.
3. **Calibrated confidence** — evidence score plus margin over runner-up,
   banded into auto_commit / review / unmatched at thresholds fitted to a
   precision floor.

Granularity mismatch is handled by **accrual, not 1:1 mapping**
(`accrual.py`): several field entries accrue against one L6 node as
quantity-weighted % complete. Nothing is silently dropped — below the
review floor an entry is raised as a possible *new* activity.

`web/app.py` derives all console state from the entries table on every
read. Deliberate: one source of truth, no cached rollup that can drift from
the entries justifying it. The single exception is `ACCRUED`, the accrued
quantity per activity, which is maintained incrementally and rebuilt on any
planner resolve — it feeds only the linker's remaining-quantity constraint
and is never read by the console. Before it existed, every ingest re-folded
the whole table (4.0 ms/entry at 335 rows rising to 24.7 ms at 2,677, i.e.
quadratic total); it is now flat at ~2 ms. Do not extend that cache to
percent complete or actual dates. `web/app.py::_anchor_to_today` shifts the sample
plan so today sits mid-execution — server only, so published accuracy
figures (computed on unshifted dates) are unaffected.

## Do not re-try these — they were measured and rejected

- **Predecessor-progress penalty.** Fires on every activity that opens a
  chain, before anything downstream is credited. Cost ~4 points of Top-1.
- **Fuzzy alias matching.** Token-set similarity over short site phrases
  collides constantly (`welding completed Sec-2` vs `Sec-4`); cost ~15
  points of auto-commit precision. Only exact, unambiguous,
  constraint-checked phrasings may bypass the ranker.
- **Alias learning as a confidence boost.** Bought +12% coverage for −16
  points of precision: it lifts every activity of the same *kind* equally,
  so it adds certainty without adding evidence. Demoted to a tie-breaker
  that changes the pick without changing claimed confidence.
- **A model's output as slot fact.** gemma3:270m, validated against the
  plan's vocabulary, still returned a valid-but-wrong area for most
  sentences. As a hard constraint that cost **−14.3 Top-1** and took the
  voice channel to 50.7%. The rule now: a model's value pre-selects a chip
  and nothing more; the linker ignores it until a person taps it. With
  that in place the same model changes no accuracy number and its
  suggestions were right 6 of 10 times. Enable a bigger model only after
  `cli agent --llm` says to.
- **The learning flywheel.** On a date-split holdout, 16 planner
  confirmations moved Top-1 by +0.0% and coverage by +0.0%. Re-measured on
  a wording split that cannot leak (a date cut puts every phrasing on both
  sides), 14 confirmations also moved both by +0.0%. Two independent
  splits, no movement. **Do not claim a flywheel.** Exact-phrase reuse
  helps with repeated DPR boilerplate and nothing more. Making corrections
  generalise is open work.

Bugs the tests caught, both of which had been inflating results: the
inch-normaliser eating the `IN` out of `LP-IN-0789`, and BM25 scores never
normalised into [0,1] (negative IDF made the divisor tiny, so one signal
swamped the rest and pinned confidence at a clipped 1.0). Also: rejecting a
queue item used to hide it, breaking the "nothing is dropped" promise.

## State of play

**Real:** ingestion of three genuinely different formats; tag grammar and
vocabulary normalisation; hybrid retrieval; constraint re-ranking;
confidence calibration; accrual; review queue with per-item reasons; audit
trail; P6 write-back payload; live web app with WebSocket push and
persistent SQLite; robustness curve and wording holdout; 56 tests.

**Scaffolded on purpose:** the plan is exchanged as CSV rather than parsed
from a P6 XER — documented, mechanical, a single-module swap (`plan.py`).

**On the synthetic data.** The PS forbids live project data and instructs
synthetic use, so this is compliance, not a shortcut. The residual risk is
that the generator and the linker share an author: `noise.py` and the
wording holdout exist to measure that rather than argue about it. What
still cannot be manufactured is a few hundred real entries with a
planner's own labels; that needs a pilot.

**Against the PS — keep this honest.**

| # | Expected outcome | State |
|---|---|---|
| 1 | Ingest heterogeneous inputs incl. Primavera exports; extract actual start/end | **Yes, bar OCR.** 3 field formats end to end, and the baseline reads from a real P6 **XER** (`plan.load_xer`). No OCR for scanned diaries — the PS excuses it. No MS Project XML reader. |
| 2 | LLM conversational / voice "time agent" replacing rigid forms | **Yes, with a measured caveat.** Conversational and voice (on-device where available, honestly labelled). A local LLM is wired in as a **gated suggester**: it fills slots the rules cannot, validated against the plan, and its values only pre-select a chip — the linker ignores them until a person confirms. Off by default because the available model made things worse (below). |
| 3 | Fuzzy-match to L5/L6; flag unmatched not dropped | **Yes** — the core. |
| 4 | Auto-update in near real time, confidence + audit trail | **Mostly.** Confidence, ~2 ms linking, a trail naming people across a 5-stage chain, and a **P6-importable update** (`p6_update.xlsx`, approved-or-certified progress only). Still no live PMIS API push. |
| 5 | Structured dataset for analytics + institutional memory | **(a) yes. (b) yes, single-project** — `memory.py`: durations by activity kind, productivity by discipline, slippage by area/discipline, delay causes attached at verification. No cross-project repository yet. |

Voice deserves care: Chrome sends audio to Google unless `processLocally`
is set and a language pack is installed. The agent detects this and
displays which mode is live, because "nothing leaves the network" is
claimed elsewhere in this repo and must not quietly stop being true at the
microphone.

**Not built:** WhatsApp transport, Whisper ASR (browser speech stands in),
Gantt overlay, live PMIS push, cross-project portfolio (module-level
globals still mean one process = one project), and dedicated surfaces for
contractor / pm / head / owner / public beyond their role definitions and
API.

## Conventions

- Deterministic core. Same input, same output — that is what makes 97.8%
  precision publishable and reproducible.
- Thresholds live in exactly one place (`models.py`) and are fitted, not
  guessed.
- A queued item must always state *why* it stopped; absence of evidence is
  a reason and gets named.
- Report negative results. The README has a "what we tried that did not
  work" section; keep it truthful and current.
