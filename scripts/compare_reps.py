"""Compare two result sets (replicates): per section/threads/env geometric-mean speed-up vs x64 in each, and the
tasks whose time differs by more than 15% between the replicates.

Usage: python scripts/compare_reps.py results/<run A> results/<run B>  -> results/<run A>/replicates.md
"""

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENVS = ["x64", "arm64ec", "arm64"]


def latest(res):
    found = {}
    for env in ENVS:
        for f in sorted((ROOT / res / env).glob("*.json")):
            d = json.loads(f.read_text())
            found[(d["section"], d["threads"], env)] = d
    return found


def geo(found, section, threads, env):
    ref, d = found.get((section, threads, "x64")), found.get((section, threads, env))
    if not ref or not d:
        return None
    logs = [math.log(ref["tasks"][t]["median_s"] / d["tasks"][t]["median_s"])
            for t in ref["tasks"] if t in d["tasks"] and d["tasks"][t]["median_s"] > 0]
    return math.exp(sum(logs) / len(logs)) if logs else None


def main():
    a_name, b_name = sys.argv[1], sys.argv[2]
    a, b = latest(a_name), latest(b_name)
    keys = sorted({(s, t) for s, t, _ in a} & {(s, t) for s, t, _ in b})
    a_dir = Path(a_name if Path(a_name).is_absolute() else ROOT / a_name)
    md = [f"# Replicates: {Path(a_name).name} vs {Path(b_name).name}", ""]
    # column labels: the <date>_<time> part of run folder names (<computer id>_<date>_<time>)
    a_name, b_name = ("_".join(Path(n).name.split("_")[-2:]) for n in (a_name, b_name))
    md += [
          "Geometric-mean speed-up vs x64 in each replicate:", "",
          f"| Section | Threads | arm64ec ({a_name}) | arm64ec ({b_name}) | arm64 ({a_name}) | arm64 ({b_name}) |",
          "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for s, t in keys:
        cells = []
        for env in ["arm64ec", "arm64"]:
            for found in (a, b):
                g = geo(found, s, t, env)
                cells.append("–" if g is None else f"{g:.2f}×")
        md.append(f"| {s} | {t} | " + " | ".join(cells) + " |")
    md += ["", "Tasks whose median time differs by more than 15% between the replicates:", "",
           "| Section | Threads | Env | Task | " + a_name + " (s) | " + b_name + " (s) | ratio |",
           "| --- | ---: | --- | --- | ---: | ---: | ---: |"]
    n = 0
    for s, t in keys:
        for env in ENVS:
            da, db = a.get((s, t, env)), b.get((s, t, env))
            if not da or not db:
                continue
            for task, ra in da["tasks"].items():
                rb = db["tasks"].get(task)
                if not rb or rb["median_s"] <= 0:
                    continue
                ratio = ra["median_s"] / rb["median_s"]
                if abs(math.log(ratio)) > math.log(1.15):
                    n += 1
                    md.append(f"| {s} | {t} | {env} | {task} | {ra['median_s']:.3f} | {rb['median_s']:.3f} | {ratio:.2f} |")
    if not n:
        md.append("| none | | | | | | |")
    out = a_dir / "replicates.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
