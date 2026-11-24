"""Summarize benchmark results: <results>/<env>/*.json -> <results>/summary.md and <results>/summary.json.

For every section and thread count, uses the latest result file of each environment present (x64, arm64ec,
arm64). Speed-up is relative to x64 (emulated on ARM64 computers, native on Intel/AMD): t_x64 / t_env, higher is
better. Output checks: task signatures are compared with x64 (relative tolerance), rendered images by mean absolute
pixel difference, and AI segmentations by Dice per label.

Usage: python scripts/compare.py <results folder>
"""

import csv
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RESULTS = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "results")
ENVS = [e for e in ["x64", "arm64ec", "arm64"] if (RESULTS / e).exists()]
REF = "x64"
OTHERS = [e for e in ENVS if e != REF]
REL_TOL = 2e-3
IGNORED_SIGNATURE_KEYS = {"bytes", "fps"}  # compressed sizes and frame rates are not output checks

ENV_DESCRIPTION = {
    "x64": "x64 Python and x64 packages",
    "arm64ec": "ARM64EC Python (native interpreter) with the same x64 packages (emulated)",
    "arm64": "native ARM64 Python and packages",
}

SECTION_TITLES = {
    "startup": "Startup and import time",
    "io": "1. File I/O and DICOM geometry",
    "numpy": "2. Vectorized Python algorithms (numpy, scipy)",
    "cpp": "3. C++ algorithms (SimpleITK, VTK)",
    "render": "4. C++ visualization (VTK, offscreen 1920x1080)",
    "ai": "5. AI segmentation (CPU)",
    "onnx": "6. ONNX Runtime vs PyTorch, MONAIAuto3DSeg network (CPU)",
}


def latest_results():
    found = {}
    for env in ENVS:
        for f in sorted((RESULTS / env).glob("*.json")):
            d = json.loads(f.read_text())
            found[(d["section"], d["threads"], env)] = (f, d)  # sorted by timestamp: last wins
    return found


def load_log():
    f = RESULTS / "load.log"
    rows = []
    if f.exists():
        for line in f.read_text().splitlines():
            parts = line.split(" ")
            if len(parts) >= 3:
                rows.append((float(parts[0]), float(parts[2]), parts[3] if len(parts) > 3 else ""))
    return rows


def foreign_load(d, rows):
    """Mean and max foreign CPU load (% of machine) during the run that produced result d: stored in the result
    by benchmark.py ("foreign_load"), or computed from the local load.log."""
    if d.get("foreign_load"):
        return {"mean": d["foreign_load"]["mean"], "max": d["foreign_load"]["max"]}
    if not rows or "start_epoch" not in d:
        return None
    start, end = d["start_epoch"], d["end_epoch"]
    vals = [v for t, v, _ in rows if start <= t <= end + 5]
    if not vals:
        return None
    return {"mean": round(sum(vals) / len(vals), 1), "max": max(vals)}


CSV_FIELDS = ["run", "computer_id", "cpu", "os", "timestamp", "env", "python_arch", "section", "threads", "task",
              "median_s", "min_s", "max_s", "first_s", "repeats", "foreign_load_mean", "foreign_load_max"]


def computer_id(d):
    """Compact hardware id (bench/sysinfo.py), or from the run folder name <id>_<YYYYMMDD>_<NNN>."""
    system = d.get("environment", {}).get("system", {})
    if system.get("cpu"):
        from bench.sysinfo import short_id
        try:
            return short_id(system)
        except Exception:
            pass
    m = re.fullmatch(r"(.+)_\d{8}_\d{3}", RESULTS.name)
    return m.group(1) if m else None


def write_csv(found):
    """<results>/tasks.csv: one row per task, environment, section and thread count (machine-readable)."""
    rows = []
    # startup results record only the environment name: use the metadata of the same environment's other results
    env_meta = {k[2]: d["environment"] for k, (f, d) in found.items() if "cpu" in d.get("environment", {})}
    for (section, threads, env), (f, d) in sorted(found.items(), key=lambda k: (
            list(SECTION_TITLES).index(k[0][0]), k[0][1], ENVS.index(k[0][2]))):
        e = d.get("environment", {})
        if "cpu" not in e:
            e = env_meta.get(env, e)
            d = dict(d, environment=e)
        system = e.get("system", {})
        os_name = " ".join(str(x) for x in (system.get("os", {}).get("name"), system.get("os", {}).get("build")) if x)             or (f"Windows {e['windows']}" if e.get("windows") else None)
        load = foreign_load(d, LOAD) or {}
        for task, r in d["tasks"].items():
            times = r.get("times_s") or []
            rows.append({"run": RESULTS.name, "computer_id": computer_id(d), "cpu": e.get("cpu"), "os": os_name,
                         "timestamp": d.get("timestamp"), "env": env, "python_arch": e.get("python_exe_arch"),
                         "section": section, "threads": threads, "task": task,
                         "median_s": round(r["median_s"], 6), "min_s": round(min(times), 6) if times else None,
                         "max_s": round(max(times), 6) if times else None,
                         "first_s": round(r["first_s"], 6) if r.get("first_s") is not None else None,
                         "repeats": len(times), "foreign_load_mean": load.get("mean"),
                         "foreign_load_max": load.get("max")})
    with (RESULTS / "tasks.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)


def compare_sig(a, b, path=""):
    """Return list of mismatch descriptions between signature a (reference) and b."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k in IGNORED_SIGNATURE_KEYS:
                continue
            if k not in b:
                out.append(f"{path}/{k} missing")
            else:
                out += compare_sig(a[k], b[k], f"{path}/{k}")
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            out.append(f"{path} length {len(a)} != {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out += compare_sig(x, y, f"{path}[{i}]")
    elif isinstance(a, bool) or isinstance(b, bool) or isinstance(a, str):
        if a != b:
            out.append(f"{path} {a} != {b}")
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if not math.isclose(a, b, rel_tol=REL_TOL, abs_tol=1e-6):
            out.append(f"{path} {a} != {b}")
    elif a != b:
        out.append(f"{path} {a} != {b}")
    return out


def image_diffs():
    """Mean absolute difference (0-255) of the saved last frames, relative to x64."""
    from PIL import Image
    res = {}
    for f in sorted((RESULTS / REF / "images").glob("*.png")):
        a = np.asarray(Image.open(f).convert("RGB"), dtype=np.float32)
        for env in OTHERS:
            g = RESULTS / env / "images" / f.name
            if g.exists():
                b = np.asarray(Image.open(g).convert("RGB"), dtype=np.float32)
                res.setdefault(f.stem, {})[env] = round(float(np.abs(a - b).mean()), 3) if a.shape == b.shape else None
    return res


def seg_dice():
    """Mean and minimum Dice over labels present in the x64 segmentation."""
    import nibabel as nib
    import nrrd

    def load(p):
        return nrrd.read(str(p))[0] if p.suffix == ".nrrd" else np.asarray(nib.load(str(p)).dataobj)

    res = {}
    ref_dir = ROOT / "data" / "work" / REF / "seg"
    for f in sorted(ref_dir.glob("*")):
        a = load(f).astype(np.int32)
        labels = [lb for lb in np.unique(a) if lb != 0]
        name = f.name.split(".")[0]
        for env in OTHERS:
            g = ROOT / "data" / "work" / env / "seg" / f.name
            if not g.exists():
                continue
            b = load(g).astype(np.int32)
            dices = []
            for lb in labels:
                x, y = a == lb, b == lb
                dices.append(2 * np.logical_and(x, y).sum() / (x.sum() + y.sum()))
            res.setdefault(name, {})[env] = {"mean": round(float(np.mean(dices)), 4),
                                             "min": round(float(np.min(dices)), 4)}
    return res


def fmt_t(t):
    return "–" if t is None else (f"{t:.3f}" if t < 10 else f"{t:.1f}")


def fmt_x(x):
    return "–" if x is None else f"{x:.2f}×"


LOAD = []


def main():
    global LOAD
    load = LOAD = load_log()
    previous = {}
    if (RESULTS / "summary.json").exists():  # output checks that need local files (images, data/work) are kept
        previous = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    found = latest_results()
    groups = sorted({(s, t) for s, t, _ in found}, key=lambda g: (list(SECTION_TITLES).index(g[0]), g[1]))
    summary = {"envs": ENVS, "groups": [], "image_diffs": {}, "seg_dice": {}, "load": {}}
    meta = next((d["environment"] for (s, t, e), (f, d) in found.items() if "cpu" in d["environment"]), {})
    emulated = meta.get("machine", "").upper() == "ARM64"  # platform.machine() reports the native architecture
    summary["machine"] = {k: meta.get(k) for k in ("cpu", "logical_cpus", "memory_gb", "windows", "machine", "system")}
    if meta.get("system", {}).get("cpu"):  # results with the bench/sysinfo.py computer description
        from bench.sysinfo import summary_line
        machine = summary_line(meta["system"])
    else:
        machine = (f"{meta.get('cpu', '?')}, {meta.get('logical_cpus', '?')} logical CPUs, "
                   f"{meta.get('memory_gb', '?')} GB RAM, Windows {meta.get('windows', '?')}")
    md = ["# Benchmark results", "",
          f"Machine: {machine}.", "",
          "Times are medians in seconds." + (
              f" Speed-up = time in x64{' (emulated)' if emulated else ''} / time in the environment; higher is better."
              if OTHERS else ""),
          "Environments: " + "; ".join(f"**{e}** = {ENV_DESCRIPTION[e]}" + (
              ", emulated (Prism)" if e == REF and emulated else "") for e in ENVS) + ".", ""]
    mismatches = []
    for section, threads in groups:
        envs = {e: found.get((section, threads, e)) for e in ENVS}
        ref = envs[REF][1] if envs.get(REF) else None
        tasks = []
        for e in ENVS:  # union in order: x64 tasks first, then tasks only some environments ran (NPU)
            if envs[e]:
                tasks += [t for t in envs[e][1]["tasks"] if t not in tasks]
        title = SECTION_TITLES.get(section, section)
        thread_txt = "" if section == "startup" else f" — {threads} thread{'s' if threads != 1 else ''}"
        md += [f"## {title}{thread_txt}", "",
               "| Task | " + " | ".join(f"{e} (s)" for e in ENVS) + "".join(f" | {e} speed-up" for e in OTHERS) + " |",
               "| --- |" + " ---: |" * (len(ENVS) + len(OTHERS))]
        logs = {e: [] for e in OTHERS}
        rows = []
        for task in tasks:
            t = {}
            for e in ENVS:
                if envs[e] and task in envs[e][1]["tasks"]:
                    t[e] = envs[e][1]["tasks"][task]["median_s"]
            sx = {e: (t[REF] / t[e]) if REF in t and e in t and t[e] > 0 else None for e in OTHERS}
            for e, v in sx.items():
                if v:
                    logs[e].append(math.log(v))
            md.append(f"| {task} | " + " | ".join(fmt_t(t.get(e)) for e in ENVS) +
                      "".join(f" | {fmt_x(sx[e])}" for e in OTHERS) + " |")
            rows.append({"task": task, "times": t, "speedup": sx})
            if ref and section != "startup" and task in ref["tasks"]:
                for e in OTHERS:
                    if envs[e] and task in envs[e][1]["tasks"]:
                        diffs = compare_sig(ref["tasks"][task]["signature"], envs[e][1]["tasks"][task]["signature"])
                        if diffs:
                            mismatches.append(f"{section} t{threads} {task} [{e}]: " + "; ".join(diffs[:3]))
        geo = {e: (math.exp(sum(v) / len(v)) if v else None) for e, v in logs.items()}
        if OTHERS:
            md.append("| **Geometric mean** |" + " |" * len(ENVS) + "".join(f" **{fmt_x(geo[e])}** |" for e in OTHERS))
        md.append("")
        loads = {e: foreign_load(envs[e][1], load) for e in ENVS if envs[e]}
        if any(loads.values()):
            md.append("CPU load from other processes during the run (% of machine, mean / max): " + ", ".join(
                f"{e} {v['mean']} / {v['max']}" for e, v in loads.items() if v))
            md.append("")
        summary["load"][f"{section}-t{threads}"] = loads
        summary["groups"].append({"section": section, "threads": threads, "rows": rows, "geomean": geo})

    if OTHERS:
        md += ["## Output checks", ""]
        summary["image_diffs"] = image_diffs() if (RESULTS / REF / "images").exists() else             previous.get("image_diffs", {})
        if summary["image_diffs"]:
            md += ["Rendered last frames, mean absolute pixel difference from x64 (0–255):", "",
                   "| Image | " + " | ".join(OTHERS) + " |", "| --- |" + " ---: |" * len(OTHERS)]
            for k, v in summary["image_diffs"].items():
                md.append(f"| {k} | " + " | ".join(str(v.get(e, "–")) for e in OTHERS) + " |")
            md.append("")
        # segmentations are written to data/work/<env>/seg by the AI section (latest run of each environment)
        # (data/work has the latest run's segmentations: computed once, then kept in summary.json)
        if previous.get("seg_dice"):
            summary["seg_dice"] = previous["seg_dice"]
        elif any(s == "ai" for s, _ in groups) and (ROOT / "data" / "work" / REF / "seg").exists():
            summary["seg_dice"] = seg_dice()
        if summary["seg_dice"]:
            md += ["AI segmentations, Dice per label against x64 (mean / minimum over labels):", "",
                   "| Segmentation | " + " | ".join(OTHERS) + " |", "| --- |" + " ---: |" * len(OTHERS)]
            for k, v in summary["seg_dice"].items():
                md.append(f"| {k} | " + " | ".join(
                    f"{v[e]['mean']} / {v[e]['min']}" if e in v else "–" for e in OTHERS) + " |")
            md.append("")
        md += [f"Task signatures that differ from x64 (relative tolerance {REL_TOL}):", ""] + (
            [f"- {m}" for m in mismatches] or ["- none"]) + [""]
    summary["signature_mismatches"] = mismatches

    (RESULTS / "summary.md").write_text("\n".join(md), encoding="utf-8")
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    write_csv(found)
    print(f"written: {RESULTS / 'summary.md'}, {RESULTS / 'tasks.csv'}")


if __name__ == "__main__":
    main()
