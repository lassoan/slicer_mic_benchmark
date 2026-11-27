"""Write the benchmark report as Markdown and HTML (self-contained, with charts).

Usage: python scripts/make_report.py <results folder> [--out <report folder>] [--replicate <results folder>]

Inputs: <results>/summary.json (scripts/compare.py), <results>/extra_checks.json (bench.extra_checks, optional),
the result JSON files (machine and package metadata), and <report folder>/findings.md (optional hand-written notes).
Outputs in the report folder (default: reports/<results folder name>): report.md, report.html, charts/*.svg.
Key findings are derived from the results automatically. Works for any subset of the environments x64, arm64ec,
arm64 (an Intel/AMD computer has only x64). Needs the "markdown" package (tools environment).
"""

import argparse
import html
import json
import math
import sys
from datetime import date
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
import compare_reps  # noqa: E402

ALL_ENVS = ["x64", "arm64ec", "arm64"]
# categorical slots 1-3 (validated all-pairs, light and dark); a color follows the environment
COLORS = {"x64": ("--s1", "#2a78d6"), "arm64ec": ("--s2", "#eb6834"), "arm64": ("--s3", "#1baf7a")}
ENV_LABEL = {"x64": "x64", "arm64ec": "ARM64EC", "arm64": "native arm64"}
SECTION_TITLE = {
    "startup": "Python startup and imports",
    "io": "1. File I/O and DICOM geometry",
    "numpy": "2. numpy/scipy",
    "cpp": "3. C++ (SimpleITK, VTK)",
    "render": "4. VTK rendering",
    "ai": "5. AI segmentation, PyTorch (CPU)",
    "onnx": "6. ONNX Runtime vs PyTorch",
    "onnx_torch": "6. MONAI network, PyTorch (CPU)",
    "onnx_ort": "6. MONAI network, ONNX Runtime (CPU)",
}
BACKEND = {"torch": "PyTorch", "onnxruntime": "ONNX Runtime (CPU)", "npu_qnn_fp16": "ONNX Runtime + QNN, NPU fp16"}
CHART_ALT = {"speedup": "Speed-up by section", "ai": "AI inference", "svd": "SVD scaling"}


# ----------------------------------------------------------------------------------------------- charts (SVG)

def fill(env):
    name, hexval = COLORS[env]
    return f"var({name},{hexval})"


def svg_wrap(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" role="img" '
            f'aria-label="{html.escape(title)}" style="max-width:{w}px;font-family:system-ui,Segoe UI,sans-serif;'
            f'font-size:12px;background:var(--surface,#fcfcfb)">{body}</svg>')


def text(x, y, s, anchor="start", color="var(--ink2,#52514e)"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}">{html.escape(s)}</text>'


def legend(x, y, envs):
    out = []
    for e in envs:
        out.append(f'<rect x="{x}" y="{y - 9}" width="10" height="10" rx="2" fill="{fill(e)}"/>')
        out.append(text(x + 14, y, ENV_LABEL[e], color="var(--ink1,#0b0b0b)"))
        x += 24 + 7 * len(ENV_LABEL[e])
    return "".join(out)


def hbar_chart(rows, envs, vmax, fmt, title, ref=None, label_w=250, w=760):
    """rows: [(label, {env: value})]; grouped horizontal bars from 0, optional dashed reference line."""
    bar, gap, group_gap, top = 12, 2, 14, 34
    plot_w = w - label_w - 60
    h = top + len(rows) * (len(envs) * (bar + gap) + group_gap) + 30
    sx = lambda v: label_w + plot_w * v / vmax  # noqa: E731
    out = [legend(label_w, 16, envs)]
    for t in [vmax * i / 4 for i in range(5)]:
        out.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h - 24}" '
                   f'stroke="var(--grid,#e4e3df)" stroke-width="1"/>')
        out.append(text(f"{sx(t):.1f}", h - 8, fmt(t), "middle"))
    y = top
    for label, vals in rows:
        gh = len(envs) * (bar + gap)
        out.append(text(label_w - 8, y + gh / 2 + 4, label, "end", "var(--ink1,#0b0b0b)"))
        for e in envs:
            v = vals.get(e)
            if v is not None:
                x1 = sx(min(v, vmax))
                out.append(f'<rect x="{label_w}" y="{y}" width="{max(x1 - label_w, 1):.1f}" height="{bar}" rx="3" '
                           f'fill="{fill(e)}"><title>{html.escape(label)} – {ENV_LABEL[e]}: {fmt(v)}</title></rect>')
                out.append(text(f"{x1 + 4:.1f}", y + bar - 2, fmt(v)))
            y += bar + gap
        y += group_gap
    if ref is not None:
        out.append(f'<line x1="{sx(ref):.1f}" x2="{sx(ref):.1f}" y1="{top - 6}" y2="{h - 24}" '
                   f'stroke="var(--ink1,#0b0b0b)" stroke-width="1.5" stroke-dasharray="4 3"/>')
    return svg_wrap(w, h, "".join(out), title)


def line_chart(series, xs, title, w=560, h=300):
    left, right, top, bottom = 50, 20, 34, 40
    ymax = max(v for s in series.values() for v in s) * 1.1
    sx = lambda i: left + (w - left - right) * i / max(len(xs) - 1, 1)  # noqa: E731
    sy = lambda v: h - bottom - (h - top - bottom) * v / ymax  # noqa: E731
    out = [legend(left, 16, list(series))]
    for t in [ymax * i / 4 for i in range(5)]:
        out.append(f'<line x1="{left}" x2="{w - right}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" stroke="var(--grid,#e4e3df)"/>')
        out.append(text(left - 6, f"{sy(t) + 4:.1f}", f"{t:.1f}", "end"))
    for i, x in enumerate(xs):
        out.append(text(f"{sx(i):.1f}", h - bottom + 18, str(x), "middle"))
    out.append(text((left + w - right) / 2, h - 4, "threads", "middle"))
    out.append(text(8, top - 8, "s"))
    for e, vals in series.items():
        pts = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(vals))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{fill(e)}" stroke-width="2"/>')
        for i, v in enumerate(vals):
            out.append(f'<circle cx="{sx(i):.1f}" cy="{sy(v):.1f}" r="4" fill="{fill(e)}" stroke="var(--surface,#fcfcfb)" '
                       f'stroke-width="2"><title>{ENV_LABEL[e]}, {xs[i]} threads: {v:.2f} s</title></circle>')
    return svg_wrap(w, h, "".join(out), title)


# ----------------------------------------------------------------------------------------------- data helpers

def machine_lines(system, power_states):
    """Markdown bullets describing the computer (from bench/sysinfo.py metadata)."""
    from bench.sysinfo import summary_lines
    lines = []
    for line in summary_lines(system):
        label, _, value = line.partition(":")
        if label.strip() in ("Python", "Power"):  # Python is in the environment table; power is per run (below)
            continue
        if label.strip() == "Arch":  # the Python process architecture is per environment (table below)
            value = system.get("architecture", {}).get("machine")
        lines.append(f"- {label.strip()}: {str(value).strip()}")
    if len(power_states) == 1:
        lines.append(f"- Power: {next(iter(power_states))}")
    elif power_states:
        lines.append("- Power: **differed between runs**: " + "; ".join(
            f"{state} ({len(runs)} run{'s' if len(runs) > 1 else ''})" for state, runs in power_states.items()))
    return lines


def geomean(xs):
    xs = [x for x in xs if x]
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else None


def fmt_s(v):
    return "–" if v is None else (f"{v:.1f}" if v >= 10 else f"{v:.3f}")


def section_label(key, threads):
    base = key.split("_")[0]
    return SECTION_TITLE[key] + (f", {threads} thread{'s' if threads > 1 else ''}"
                                 if base in ("numpy", "cpp", "render") else "")


def section_speedups(groups, others):
    """{(key, threads): {env: geometric-mean speed-up}}; section 6 split into PyTorch and ONNX Runtime (CPU)."""
    head = {}
    for g in groups:
        subsets = ([("onnx_torch", "_torch_"), ("onnx_ort", "_onnxruntime_")] if g["section"] == "onnx"
                   else [(g["section"], "")])
        for key, sub in subsets:
            rows = [r for r in g["rows"] if sub in r["task"] + "_" and "npu" not in r["task"]]
            head[(key, g["threads"])] = {e: geomean([r["speedup"].get(e) for r in rows]) for e in others}
    return head


def ai_backends(groups):
    """{backend: {env: [per-case times]}} and the case list, from section 6 sliding-window tasks."""
    onnx = next((g for g in groups if g["section"] == "onnx"), None)
    if not onnx:
        return {}, []
    cases = sorted({r["task"].rsplit("_", 1)[1] for r in onnx["rows"] if r["task"].startswith("6b_")})
    out = {}
    for b in BACKEND:
        for c in cases:
            r = next((r for r in onnx["rows"] if r["task"] == f"6b_sliding_window_{b}_{c}"), None)
            for e, v in (r["times"] if r else {}).items():
                out.setdefault(b, {}).setdefault(e, [None] * len(cases))[cases.index(c)] = v
    return out, cases


def later_note(row):
    """'run 2026-11-27, 3 days after the rest of this run' for a task added to the run later, else ''."""
    later = (row or {}).get("run_later", {})
    return "; ".join(f"run {v['date']}, {v['days_later']} day{'s' if v['days_later'] != 1 else ''} after the rest "
                     f"of this run" if v["days_later"] > 0 else f"run {v['date']}, separately from the rest of this run"
                     for v in later.values())


def totalseg_full(groups):
    """[(case, [(label, seconds)], note)]: TotalSegmentator full resolution with PyTorch (task 5b, each environment)
    and with the networks on the NPU (task 6c), for the cases that ran on the NPU; note: when 6c was run later."""
    rows = {g["section"]: {r["task"]: r for r in g["rows"]} for g in groups if g["section"] in ("ai", "onnx")}
    out = []
    for task, row in rows.get("onnx", {}).items():
        if not task.startswith("6c_totalseg_full_npu_qnn_fp16_"):
            continue
        case = task.rsplit("_", 1)[1]
        torch_times = rows.get("ai", {}).get(f"5b_totalseg_full_{case}", {}).get("times", {})
        cols = [(f"PyTorch, {ENV_LABEL[e]}", t) for e, t in torch_times.items() if t]
        cols += [(f"{BACKEND['npu_qnn_fp16']}, {ENV_LABEL[e]}", t) for e, t in row["times"].items() if t]
        out.append((case, cols, later_note(row)))
    return out


# ----------------------------------------------------------------------------------------------- findings

def auto_findings(summary, head, envs, others, emulated, extra, backends):
    groups = summary["groups"]
    f = []
    ref = "x64 (emulated)" if emulated else "x64"
    for e in others:
        vals = {k: v[e] for k, v in head.items() if v.get(e)}
        non_ai = [v for (k, _), v in vals.items() if k not in ("ai", "onnx_torch", "onnx_ort")]
        if not non_ai:
            continue
        rows = [(r["speedup"][e], r["task"], g["section"], g["threads"]) for g in groups for r in g["rows"]
                if r["speedup"].get(e) and g["section"] not in ("ai", "onnx")]
        rows.sort()
        top, low = {}, {}
        for x, t, s, th in rows[::-1]:
            top.setdefault(t, x)
        for x, t, s, th in rows:
            low.setdefault(t, x)
        best = ", ".join(f"`{t}` {x:.2f}×" for t, x in list(top.items())[:4])
        worst = ", ".join(f"`{t}` {x:.2f}×" for t, x in list(low.items())[:3] if x < 0.95)
        line = (f"**{ENV_LABEL[e]} vs {ref}:** {geomean(non_ai):.2f}× overall without AI (geometric mean of "
                f"sections, range {min(non_ai):.2f}–{max(non_ai):.2f}×). Largest gains: {best}.")
        if worst:
            line += f" Slower: {worst}."
        ai = vals.get(("ai", next((t for k, t in vals if k == "ai"), 0)))
        if ai:
            line += f" AI segmentation with PyTorch: {ai:.2f}×."
        f.append(line)
    for e in envs:
        scal = []
        for sec in ("numpy", "cpp", "render"):
            gs = sorted((g for g in groups if g["section"] == sec), key=lambda g: g["threads"])
            if len(gs) >= 2:
                one, many = gs[0], gs[-1]
                r = geomean([a["times"][e] / b["times"][e] for a in one["rows"] for b in many["rows"]
                             if a["task"] == b["task"] and e in a["times"] and e in b["times"] and b["times"][e] > 0])
                if r:
                    scal.append(f"{SECTION_TITLE[sec]} {r:.2f}×")
                    nthreads = many["threads"]
        if scal:
            f.append(f"**Multithreading ({ENV_LABEL[e]}):** speed-up with {nthreads} threads over 1 thread "
                     f"(geometric mean over tasks): " + ", ".join(scal) + ".")
    if backends:
        totals = [(sum(v for v in ts if v), b, e) for b, d in backends.items() for e, ts in d.items()
                  if all(v is not None for v in ts)]
        totals.sort()
        if totals:
            t0, b0, e0 = totals[0]
            parts = [f"{t / t0:.1f}× faster than {BACKEND[b]} on {ENV_LABEL[e]}" for t, b, e in totals[1:]]
            f.append(f"**Fastest AI inference** (MONAIAuto3DSeg network, sliding window, {len(backends[b0][e0])} "
                     f"cases): {BACKEND[b0]} on {ENV_LABEL[e0]}, {t0:.1f} s in total; " + ", ".join(parts) + ".")
    for case, cols, note in totalseg_full(groups):
        npu = [t for lbl, t in cols if "NPU" in lbl]
        others_t = [(lbl, t) for lbl, t in cols if "NPU" not in lbl]
        if npu and others_t:
            f.append(f"**TotalSegmentator full resolution on the NPU** ({case}{'; ' + note if note else ''}): {npu[0] / 60:.1f} min; " +
                     ", ".join(
                f"{t / npu[0]:.1f}× faster than {lbl} ({t / 60:.1f} min)" for lbl, t in others_t) + ".")
    if extra:
        for e in envs:
            svd = {int(k): v for k, v in extra.get(e, {}).get("svd_2000_s", {}).items()}
            if svd:
                tbest = min(svd, key=svd.get)
                tmax = max(svd)
                if tbest < tmax and svd[tmax] > svd[tbest] * 1.05:
                    f.append(f"**Linear algebra threading ({ENV_LABEL[e]}):** a 2000×2000 SVD is fastest with "
                             f"{tbest} threads ({svd[tbest]:.2f} s); with {tmax} threads it takes {svd[tmax]:.2f} s.")
        zl = {e: extra[e]["zlib"] for e in envs if "zlib" in extra.get(e, {})}
        if len({z["version"] for z in zl.values()}) > 1:
            f.append("**zlib differs between environments:** " + ", ".join(
                f"{ENV_LABEL[e]} {z['version']} ({z['compress_64MB_s']:.2f} s, {z['ratio'] * 100:.0f}% size)"
                for e, z in zl.items()) + " for 64 MB at level 1; gzip task times are not comparable.")
    if others:
        mism = summary.get("signature_mismatches", [])
        dice = [v["min"] for d in summary.get("seg_dice", {}).values() for v in d.values() if v]
        img = [v for d in summary.get("image_diffs", {}).values() for v in d.values() if v is not None]
        f.append("**Output agreement with x64:** " + "; ".join(filter(None, [
            f"rendered images max. mean pixel difference {max(img):.2f}" if img else "",
            f"segmentation minimum per-label Dice {min(dice):.4f}" if dice else "",
            f"{len(mism)} task result(s) differ: " + "; ".join(f"`{m}`" for m in mism) if mism
            else "all task results match"])) + ".")
    loaded = [f"{k} {e} ({v['mean']} / {v['max']}%)" for k, d in summary.get("load", {}).items()
              for e, v in (d or {}).items() if v and (v["mean"] >= 4 or v["max"] >= 20)]
    if loaded:
        f.append("**Runs that overlapped CPU load from other processes** (mean / max % of machine): " +
                 ", ".join(loaded) + ". Their times may be too long.")
    return "\n".join(f"- {x}" for x in f)


# ----------------------------------------------------------------------------------------------- report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("results")
    p.add_argument("--out")
    p.add_argument("--replicate")
    args = p.parse_args()
    resdir = Path(args.results).resolve()
    out = Path(args.out).resolve() if args.out else ROOT / "reports" / resdir.name
    (out / "charts").mkdir(parents=True, exist_ok=True)
    summary = json.loads((resdir / "summary.json").read_text(encoding="utf-8"))
    extra_file = resdir / "extra_checks.json"
    extra = json.loads(extra_file.read_text(encoding="utf-8")) if extra_file.exists() else {}
    envs = [e for e in ALL_ENVS if (resdir / e).exists()]
    others = [e for e in envs if e != "x64"]

    meta, power_states = {}, {}
    for env in envs:
        for f in sorted((resdir / env).glob("*.json"), reverse=True):
            d = json.loads(f.read_text())
            env_meta = d.get("environment", {})
            if "cpu" in env_meta:
                meta.setdefault(env, env_meta)
            p = env_meta.get("system", {}).get("power")
            if p:
                state = ", ".join(str(p[k]) for k in ("source", "plan", "mode") if p.get(k))
                power_states.setdefault(state, []).append(f"{env}/{f.stem}")
    m = next(iter(meta.values()))
    # computer description (bench/sysinfo.py, newer results only), preferably from an environment that runs natively
    system = next((meta[e]["system"] for e in reversed(envs)
                   if meta.get(e, {}).get("system", {}).get("cpu")
                   and not meta[e]["system"].get("architecture", {}).get("emulated")), None) \
        or next((meta[e]["system"] for e in envs if meta.get(e, {}).get("system", {}).get("cpu")), None)
    emulated = m["machine"].upper() == "ARM64"
    ENV_LABEL["x64"] = "x64 (emulated)" if emulated else "x64"
    groups = summary["groups"]
    head = section_speedups(groups, others)
    backends, cases = ai_backends(groups)

    charts = {}
    rows = [(section_label(k, t), v) for (k, t), v in head.items() if any(v.values())]
    if others and rows:
        vmax = max(2.0, math.ceil(max(x for _, v in rows for x in v.values() if x) * 2) / 2)
        charts["speedup"] = hbar_chart(rows, others, vmax, lambda v: f"{v:.2f}×",
                                       "Speed-up vs x64 by section (dashed line: 1.0 = same as x64)", ref=1.0)
    if backends:
        tot = [(BACKEND[b], {e: sum(ts) for e, ts in d.items() if all(v is not None for v in ts)})
               for b, d in backends.items()]
        vmax = max(v for _, d in tot for v in d.values())
        step = 10 ** math.floor(math.log10(vmax))
        charts["ai"] = hbar_chart(tot, [e for e in envs if any(e in d for _, d in tot)],
                                  math.ceil(vmax / step) * step, lambda v: f"{v:.0f} s",
                                  f"MONAIAuto3DSeg sliding-window inference, total time for {len(cases)} cases "
                                  "(lower is better)", label_w=210)
    svd_envs = [e for e in envs if "svd_2000_s" in extra.get(e, {})]
    if svd_envs:
        xs = sorted({int(k) for e in svd_envs for k in extra[e]["svd_2000_s"]})
        charts["svd"] = line_chart({e: [extra[e]["svd_2000_s"][str(x)] for x in xs] for e in svd_envs}, xs,
                                   "2000×2000 SVD time vs thread count (lower is better)")
    for k, svg in charts.items():
        (out / "charts" / f"{k}.svg").write_text(svg, encoding="utf-8")

    title = f"Medical image computing benchmark — {m.get('cpu', '?')}"
    md = [f"# {title}", "",
          f"Results `{resdir.name}`, report generated {date.today().isoformat()}.", "",
          "## Machine and environments", ""]
    if system:
        md += machine_lines(system, power_states)
    else:  # results written before bench/sysinfo.py existed
        md += [f"- CPU: {m['cpu']}, {m['logical_cpus']} logical CPUs, {m['memory_gb']} GB RAM",
               f"- Windows {m['windows']}, native architecture {'ARM64' if emulated else m['machine']}"]
    md += ["", "| Environment | Interpreter | Packages | Emulated |", "| --- | --- | --- | --- |"]
    desc = {"x64": ("python.org CPython x64", "`win_amd64` wheels", "everything" if emulated else "nothing"),
            "arm64ec": ("ARM64EC CPython build", "the same `win_amd64` wheels", "extension modules only"),
            "arm64": ("python.org CPython ARM64", "`win_arm64` wheels", "nothing")}
    for e in envs:
        md.append(f"| {ENV_LABEL[e]} | " + " | ".join(desc[e]) + " |")
    md += ["", f"Python {m['python'].split()[0]}. Package versions:", "",
           "| Package | " + " | ".join(envs) + " |", "| --- | " + " | ".join("---" for _ in envs) + " |"]
    for pkg in m["packages"]:
        md.append(f"| {pkg} | " + " | ".join(meta.get(e, {}).get("packages", {}).get(pkg, "–") for e in envs) + " |")
    md.append("")

    md += ["## Key findings", "", auto_findings(summary, head, envs, others, emulated, extra, backends), ""]
    # hand-written analysis: <results folder>/findings.md (published), or <report folder>/findings.md (local)
    notes = next((f for f in (resdir / "findings.md", out / "findings.md") if f.exists()), None)
    if notes:
        lines = notes.read_text(encoding="utf-8").strip().splitlines()
        if lines and lines[0].startswith("# "):  # its own title; the report has one
            lines = lines[1:]
        # nest its headings under "### Notes"
        lines = ["##" + ln if ln.startswith("#") else ln for ln in lines]
        md += ["### Notes", "", "\n".join(lines).strip(), ""]

    md += ["## Time per section", "",
           "Sum of the task times (medians, seconds) in each section; lower is better.", "",
           "| Section | Threads | " + " | ".join(ENV_LABEL[e] for e in envs) + " |",
           "| --- | ---: |" + " ---: |" * len(envs)]
    for g in groups:
        tot = {e: sum(r["times"][e] for r in g["rows"] if e in r["times"]) for e in envs}
        md.append(f"| {SECTION_TITLE[g['section']]} | {g['threads'] or '–'} | " + " | ".join(
            fmt_s(tot[e]) if tot[e] else "–" for e in envs) + " |")
    md.append("")

    if "speedup" in charts:
        md += ["## Speed-up by section", "",
               f"Speed-up = time in {ENV_LABEL['x64']} / time in the environment; higher is better. Geometric mean "
               "over the tasks of each section. Section 6 rows compare each backend with the same backend on x64.",
               "", "![Speed-up by section](charts/speedup.svg)", "",
               "| Section | Threads | " + " | ".join(ENV_LABEL[e] for e in others) + " |",
               "| --- | ---: |" + " ---: |" * len(others)]
        for (k, t), v in head.items():
            md.append(f"| {SECTION_TITLE[k]} | {t or '–'} | " + " | ".join(
                f"{v[e]:.2f}×" if v.get(e) else "–" for e in others) + " |")
        md.append("")

    if backends:
        md += ["## AI inference backends", "",
               "MONAIAuto3DSeg network (abdominal-organs-3mm), sliding-window inference per case (ROI 112×112×144, "
               "overlap 0.625), all threads.", "", "![AI inference](charts/ai.svg)", "",
               "| Backend | Environment | " + " | ".join(cases) + " |",
               "| --- | --- |" + " ---: |" * len(cases)]
        for b, d in backends.items():
            for e in envs:
                if e in d:
                    md.append(f"| {BACKEND[b]} | {ENV_LABEL[e]} | " + " | ".join(
                        "–" if v is None else f"{v:.1f} s" for v in d[e]) + " |")
        md.append("")
        if "npu_qnn_fp16" in backends:
            md += ["The NPU runs the whole network (no CPU fallback) from a precompiled QNN context model.", ""]

    ts_full = totalseg_full(groups)
    if ts_full:
        md += ["## TotalSegmentator full resolution on the NPU", "",
               "Task `total` at 1.5 mm, the same TotalSegmentator call as task 5b, with its 5 nnU-Net networks "
               "evaluated on the NPU (task 6c, fp16, no CPU fallback). Preprocessing, resampling and the sliding "
               "window run on the CPU as in 5b.", "",
               "| Case | Configuration | Time | Speed-up of NPU |", "| --- | --- | ---: | ---: |"]
        for case, cols, note in ts_full:
            npu = next((t for lbl, t in cols if "NPU" in lbl), None)
            for lbl, t in cols:
                md.append(f"| {case} | {lbl}{f' ({note})' if note and 'NPU' in lbl else ''} | {t / 60:.1f} min | " +
                          (f"{t / npu:.1f}× |" if npu else "– |"))
        md.append("")
        notes = sorted({note for _, _, note in ts_full if note})
        if notes:
            md += ["The NPU task was added to this run later (" + "; ".join(notes) + "), in the same environments. "
                   "The PyTorch times are from the original run.", ""]

    if extra:
        md += ["## Other checks", ""]
        if svd_envs:
            md += ["### Linear algebra thread scaling", "", "![SVD scaling](charts/svd.svg)", "",
                   "| Threads | " + " | ".join(ENV_LABEL[e] for e in svd_envs) + " |",
                   "| ---: |" + " ---: |" * len(svd_envs)]
            for x in xs:
                md.append(f"| {x} | " + " | ".join(f"{extra[e]['svd_2000_s'][str(x)]:.2f} s" for e in svd_envs) + " |")
            md.append("")
        zl = [e for e in envs if "zlib" in extra.get(e, {})]
        if zl:
            md += ["### zlib (64 MB of CT data, level 1)", "",
                   "| Environment | zlib | Compress | Decompress | Compressed size |", "| --- | --- | ---: | ---: | ---: |"]
            for e in zl:
                z = extra[e]["zlib"]
                md.append(f"| {ENV_LABEL[e]} | {z['version']} | {z['compress_64MB_s']:.2f} s | "
                          f"{z['decompress_64MB_s']:.2f} s | {z['ratio'] * 100:.0f}% |")
            md.append("")

    if args.replicate:
        rep = Path(args.replicate).resolve()
        a, b = compare_reps.latest(resdir), compare_reps.latest(rep)
        md += ["## Replicate agreement", "",
               f"Geometric-mean speed-up vs x64 in this run (`{resdir.name}`) and in `{rep.name}`.", "",
               "| Section | Threads | " + " | ".join(f"{ENV_LABEL[e]} ({n})" for e in others
                                                    for n in (resdir.name, rep.name)) + " |",
               "| --- | ---: |" + " ---: |" * (2 * len(others))]
        for s, t in sorted({(s, t) for s, t, _ in a} & {(s, t) for s, t, _ in b}):
            cells = []
            for e in others:
                for found in (a, b):
                    g = compare_reps.geo(found, s, t, e)
                    cells.append("–" if g is None else f"{g:.2f}×")
            md.append(f"| {SECTION_TITLE[s]} | {t or '–'} | " + " | ".join(cells) + " |")
        md.append("")

    md += ["## Task details", "", "Times are medians in seconds" + ("; speed-up vs x64." if others else "."), ""]
    for g in groups:
        s, t = g["section"], g["threads"]
        md += [f"### {SECTION_TITLE[s]}" + (f" — {t} thread{'s' if t > 1 else ''}" if t else ""), "",
               "| Task | " + " | ".join(f"{e} (s)" for e in envs) + "".join(f" | {e}" for e in others) + " |",
               "| --- |" + " ---: |" * (len(envs) + len(others))]
        for r in g["rows"]:
            sp = r.get("speedup", {})
            md.append(f"| {r['task']} | " + " | ".join(fmt_s(r["times"].get(e)) for e in envs) + "".join(
                f" | {sp[e]:.2f}×" if sp.get(e) else " | –" for e in others) + " |")
        md.append("")

    md += ["## Method", "",
           "- Test data: 20 abdominal CT series from the NCI Imaging Data Commons (IDC), listed in "
           "`manifest/idc_series.csv`; attribution in `manifest/ATTRIBUTION.md`.",
           "- Each task time is the median of the timed repeats after a warm-up (AI: one run per case). Before each "
           "run the driver waits until other processes leave the CPU idle; their CPU load is logged and runs that "
           "overlapped it are repeated once.",
           "- Design, task parameters and package differences: `METHOD.md` in the benchmark repository.",
           ""]

    md_text = "\n".join(md)
    (out / "report.md").write_text(md_text, encoding="utf-8")

    body = markdown.markdown(md_text, extensions=["tables"])
    for k, svg in charts.items():
        body = body.replace(f'<img alt="{CHART_ALT[k]}" src="charts/{k}.svg" />', f"<figure>{svg}</figure>")
    page = PAGE.replace("{title}", html.escape("Benchmark Report")).replace("{body}", body)
    (out / "report.html").write_text(page, encoding="utf-8")
    print(f"written: {out / 'report.md'}\nwritten: {out / 'report.html'}")


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root { color-scheme: light; --surface:#fcfcfb; --bg:#ffffff; --ink1:#0b0b0b; --ink2:#52514e; --grid:#e4e3df;
  --line:#d9d8d3; --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --code:#f1f0ec; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark; --surface:#1a1a19;
  --bg:#121211; --ink1:#f0efec; --ink2:#c3c2b7; --grid:#33332f; --line:#3a3a36; --s1:#3987e5; --s2:#d95926;
  --s3:#199e70; --code:#262624; } }
:root[data-theme="dark"] { color-scheme: dark; --surface:#1a1a19; --bg:#121211; --ink1:#f0efec; --ink2:#c3c2b7;
  --grid:#33332f; --line:#3a3a36; --s1:#3987e5; --s2:#d95926; --s3:#199e70; --code:#262624; }
body { background:var(--bg); color:var(--ink1); font:15px/1.55 system-ui,"Segoe UI",sans-serif; margin:0; }
main { max-width:960px; margin:0 auto; padding:24px 16px 64px; }
h1 { font-size:1.6rem; line-height:1.25; } h2 { margin-top:2.2em; border-bottom:1px solid var(--line);
  padding-bottom:4px; } h3 { margin-top:1.6em; }
table { border-collapse:collapse; margin:12px 0; font-size:13px; display:block; overflow-x:auto; max-width:100%; }
th, td { border-bottom:1px solid var(--line); padding:4px 10px; text-align:left; white-space:nowrap;
  font-variant-numeric:tabular-nums; }
th { color:var(--ink2); font-weight:600; }
code { background:var(--code); padding:1px 4px; border-radius:4px; font-size:.9em; }
figure { margin:16px 0; background:var(--surface); border:1px solid var(--line); border-radius:8px; padding:8px; }
</style></head>
<body><main>
{body}
</main></body></html>
"""


if __name__ == "__main__":
    main()
