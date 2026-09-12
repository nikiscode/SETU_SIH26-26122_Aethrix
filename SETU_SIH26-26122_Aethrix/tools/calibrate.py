"""Diagnostic: is retrieval bad, or is the confidence scale mis-set?

Prints Top-1/Top-3 ignoring bands, then the distribution of the raw blended
score split by whether the top candidate was actually correct. The gap
between those two distributions is what the thresholds should sit in.
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

ROOT = Path(__file__).resolve().parent.parent
pipe = Pipeline(ROOT / "data/baseline_schedule.csv")
res = pipe.run(ROOT / "data/inputs")
gold = load_gold(ROOT / "data/gold_labels.csv")

real = [e for e, g in gold.items() if g and e in res["links"]]
links = res["links"]

top1 = sum(1 for e in real if links[e].candidates
           and links[e].candidates[0].activity_id == gold[e])
top3 = sum(1 for e in real
           if gold[e] in [c.activity_id for c in links[e].candidates[:3]])
top5 = sum(1 for e in real
           if gold[e] in [c.activity_id for c in links[e].candidates[:5]])
print(f"retrieval only (bands ignored), n={len(real)}")
print(f"  top1 {top1/len(real):.1%}   top3 {top3/len(real):.1%}"
      f"   top5 {top5/len(real):.1%}")

ok, bad = [], []
ok_parts, bad_parts = [], []
for e in real:
    c = links[e].candidates[0] if links[e].candidates else None
    if not c:
        continue
    (ok if c.activity_id == gold[e] else bad).append(links[e].confidence)
    (ok_parts if c.activity_id == gold[e] else bad_parts).append(
        (c.lexical, c.bm25, float(c.tag_hit), c.constraint_score, c.score))


def dist(name, xs):
    a = np.array(xs)
    if not len(a):
        print(f"  {name}: none")
        return
    q = np.percentile(a, [5, 25, 50, 75, 95])
    print(f"  {name:<8} n={len(a):<4} "
          + " ".join(f"p{p}={v:.3f}" for p, v in zip([5, 25, 50, 75, 95], q)))


print("\nconfidence distribution")
dist("correct", ok)
dist("wrong", bad)

print("\ncomponent medians (lex, bm25, tag, constraint, blended)")
for nm, parts in (("correct", ok_parts), ("wrong", bad_parts)):
    if parts:
        m = np.median(np.array(parts), axis=0)
        print(f"  {nm:<8} " + "  ".join(f"{v:.3f}" for v in m))

print("\ntag coverage")
tagged = [e for e in real if res_ev.tags] if False else None
evs = {ev.event_id: ev for ev in res["events"]}
n_tag = sum(1 for e in real if evs[e].tags)
print(f"  events carrying an engineering tag: {n_tag}/{len(real)}"
      f" = {n_tag/len(real):.1%}")
n_tag_ok = sum(1 for e in real if evs[e].tags
               and links[e].candidates
               and links[e].candidates[0].activity_id == gold[e])
print(f"  top1 among tagged:   {n_tag_ok}/{n_tag}"
      f" = {n_tag_ok/max(n_tag,1):.1%}")
n_untag = len(real) - n_tag
n_untag_ok = top1 - n_tag_ok
print(f"  top1 among untagged: {n_untag_ok}/{n_untag}"
      f" = {n_untag_ok/max(n_untag,1):.1%}")
