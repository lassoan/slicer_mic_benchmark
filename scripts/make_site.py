"""Build the results website (GitHub Pages) from the committed results: an index of all runs and the report of
each run, with the CSV and JSON summaries next to them. Needs only the "markdown" package.

Usage: python scripts/make_site.py [output folder=site]
"""

import shutil
import subprocess
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import collect_results  # noqa: E402
from make_report import PAGE  # noqa: E402

REPO_URL = "https://github.com/lassoan/slicer_mic_benchmark"


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "site").resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    collect_results.main()
    shutil.copy(collect_results.RESULTS / "all.csv", out / "all.csv")
    infos = []
    for d in collect_results.runs():
        info = collect_results.run_info(d)
        infos.append(info)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "make_report.py"), str(d), "--out",
                        str(out / d.name)], check=True)
        for f in ("tasks.csv", "summary.json", "summary.md"):
            if (d / f).exists():
                shutil.copy(d / f, out / d.name / f)
        shutil.rmtree(out / d.name / "charts", ignore_errors=True)  # built into report.html
        (out / d.name / "report.md").unlink(missing_ok=True)
    md = ["# Medical image computing benchmark results", "",
          "Python on Windows: x64 (emulated on ARM64 computers), native ARM64, ARM64EC; CPU, GPU and NPU. "
          f"Source code, method and raw results: [{REPO_URL.split('/', 3)[3]}]({REPO_URL}).", "",
          "Machine-readable: [all.csv](all.csv) (every task of every run), and `tasks.csv` / `summary.json` per run.",
          "", "| Date | Computer | Environments | Speed-up vs x64 (non-AI tasks) | Report | Data |",
          "| --- | --- | --- | --- | --- | --- |"]
    for i in infos:
        sp = ", ".join(f"{e} {v:.2f}×" for e, v in i["speedups"].items()) or "–"
        md.append(f"| {i['date']} | {i['description']} | {', '.join(i['envs'])} | {sp} | "
                  f"[report]({i['name']}/report.html) | [csv]({i['name']}/tasks.csv), "
                  f"[json]({i['name']}/summary.json) |")
    body = markdown.markdown("\n".join(md), extensions=["tables"])
    (out / "index.html").write_text(PAGE.replace("{title}", "Benchmark Results").replace("{body}", body),
                                    encoding="utf-8")
    (out / ".nojekyll").write_text("")
    print(f"site: {out / 'index.html'} ({len(infos)} runs)")


if __name__ == "__main__":
    main()
