"""Combine all runs: results/*/tasks.csv -> results/all.csv (machine-readable, one row per task) and
results/README.md (human-readable index of the runs, shown by GitHub when browsing the results folder).

Usage: python scripts/collect_results.py
"""

import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RESULTS = ROOT / "results"


def runs():
    """Run folders with a summary, newest first."""
    found = [d for d in RESULTS.iterdir() if d.is_dir() and (d / "summary.json").exists()]
    return sorted(found, key=lambda d: d.name.rsplit("_", 2)[-2:], reverse=True)


def run_info(d):
    summary = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    machine = summary.get("machine", {})
    system = machine.get("system") or {}
    if system.get("cpu"):
        from bench.sysinfo import summary_line
        desc = summary_line(system).replace(" | ", ", ")  # "|" would split the Markdown table cell
    else:
        desc = f"{machine.get('cpu', '?')}, {machine.get('logical_cpus', '?')} logical CPUs, " \
               f"{machine.get('memory_gb', '?')} GB RAM, Windows {machine.get('windows', '?')}"
    speedups = {}
    for e in summary.get("envs", []):
        if e == "x64":
            continue
        logs = [math.log(r["speedup"][e]) for g in summary["groups"] if g["section"] not in ("ai", "onnx")
                for r in g["rows"] if r.get("speedup", {}).get(e)]
        if logs:
            speedups[e] = math.exp(sum(logs) / len(logs))
    date = d.name.rsplit("_", 2)[-2] if d.name.count("_") >= 2 else ""
    return {"name": d.name, "date": f"{date[:4]}-{date[4:6]}-{date[6:]}" if len(date) == 8 else "",
            "description": desc, "envs": summary.get("envs", []), "speedups": speedups}


def main():
    all_rows, fields = [], None
    infos = []
    for d in runs():
        infos.append(run_info(d))
        f = d / "tasks.csv"
        if f.exists():
            with f.open(newline="", encoding="utf-8") as fh:
                r = csv.DictReader(fh)
                fields = fields or r.fieldnames
                all_rows += list(r)
    if fields:
        with (RESULTS / "all.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(all_rows)
    md = ["# Benchmark results", "",
          "One folder per benchmark run: `<computer id>_<date>_<time of day as 000-999>`. How to run the benchmark "
          "and add a run: [RUNNING.md](../RUNNING.md).", "",
          "Human-readable, per run:", "",
          "- `<run>/findings.md`: conclusions and caveats, written by whoever ran the benchmark (if present)",
          "- `<run>/summary.md`: every task with times and speed-ups",
          "- the report with charts: the repository's results website", "",
          "Machine-readable:", "",
          "- [all.csv](all.csv): every task of every run, one row per task, environment and thread count "
          "(columns: run, computer_id, cpu, os, timestamp, env, python_arch, section, threads, task, median_s, "
          "min_s, max_s, first_s, repeats, foreign_load_mean, foreign_load_max)",
          "- `<run>/tasks.csv`: the same for one run; `<run>/<env>/*.json`: raw results with full metadata;"
          " `<run>/summary.json`: per-task times and speed-ups, output checks", "",
          "Speed-up = geometric mean over the non-AI tasks of time in x64 / time in the environment (x64 is emulated "
          "on ARM64 computers).", "",
          "| Date | Computer | Environments | Speed-up vs x64 | Run |", "| --- | --- | --- | --- | --- |"]
    for i in infos:
        sp = ", ".join(f"{e} {v:.2f}×" for e, v in i["speedups"].items()) or "–"
        links = [f"[summary]({i['name']}/summary.md)", f"[csv]({i['name']}/tasks.csv)"]
        if (RESULTS / i["name"] / "findings.md").exists():
            links.insert(0, f"[findings]({i['name']}/findings.md)")
        md.append(f"| {i['date']} | {i['description']} | {', '.join(i['envs'])} | {sp} | {', '.join(links)} |")
    (RESULTS / "README.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"written: {RESULTS / 'all.csv'} ({len(all_rows)} rows), {RESULTS / 'README.md'} ({len(infos)} runs)")


if __name__ == "__main__":
    main()
