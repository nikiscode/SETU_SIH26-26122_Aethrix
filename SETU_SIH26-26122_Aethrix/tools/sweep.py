"""Threshold sweep.

Auto-commit precision is the metric that matters, because a wrong
auto-commit silently corrupts the baseline while a missed one merely costs
a planner ten seconds in the review queue. So thresholds are chosen as the
highest coverage that still clears a precision floor, rather than picked by
eye.
"""
import sys
from pathlib import Path

# Run as a plain script from anywhere: these live outside the package, so
# without this the "from setu..." imports below fail with ModuleNotFoundError
# unless the caller happens to have set PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from setu.evaluate import load_gold
from setu.pipeline import Pipeline

PRECISION_FLOOR = 0.97

ROOT = Path(__file__).resolve().parent.parent
pipe = Pipeline(ROOT / "data/baseline_schedule.csv")
res = pipe.run(ROOT / "data/inputs")
gold = load_gold(ROOT / "data/gold_labels.csv")
links = res["links"]

real = [e for e, g in gold.items() if g and e in links]
new = [e for e, g in gold.items() if g is None and e in links]

pairs = [(links[e].confidence, links[e].activity_id == gold[e]) for e in real]
new_conf = [links[e].confidence for e in new]

print(f"n_linkable={len(real)}  n_genuinely_new={len(new)}")
print(f"{'auto_thr':>9} {'cover':>7} {'prec':>7} {'newflag@floor':>14}")

best = None
for thr in np.arange(0.40, 0.95, 0.01):
    sel = [ok for c, ok in pairs if c >= thr]
    if not sel:
        continue
    prec = sum(sel) / len(sel)
    cover = len(sel) / len(pairs)
    if prec >= PRECISION_FLOOR and (best is None or cover > best[1]):
        best = (thr, cover, prec)
    if abs(thr * 100 % 5) < 1e-6:
        print(f"{thr:>9.2f} {cover:>7.1%} {prec:>7.1%}")

if best:
    print(f"\nbest auto-commit threshold >= {PRECISION_FLOOR:.0%} precision: "
          f"{best[0]:.2f}  coverage {best[1]:.1%}  precision {best[2]:.1%}")

print("\nreview floor — where do genuinely-new items sit?")
if new_conf:
    q = np.percentile(new_conf, [50, 75, 90, 95, 100])
    print("  new-item confidence percentiles "
          + " ".join(f"p{p}={v:.3f}" for p, v in zip([50, 75, 90, 95, 100], q)))
for floor in (0.35, 0.40, 0.45, 0.50, 0.55):
    flagged = sum(1 for c in new_conf if c < floor)
    lost = sum(1 for c, ok in pairs if ok and c < floor)
    print(f"  floor {floor:.2f}: new flagged {flagged}/{len(new_conf)}"
          f"  correct-links dropped below floor {lost}")
