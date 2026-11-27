"""Medical image computing benchmark driver (Windows, x64 or ARM64). Needs only Python 3.9+ to start.

  python benchmark.py all                 setup + data + run + report (about 4-8 hours, ~15 GB disk)
  python benchmark.py setup               base interpreters and virtual environments in .envs/
  python benchmark.py data                test data (IDC), AI models, ONNX models, NPU context model
  python benchmark.py run [options]       run the benchmark, then write the report
  python benchmark.py report [options]    (re)write results/<id>/summary.* and reports/<id>/report.* (newest run)

Results go to results/<computer id>_<date>_<time of day as 000-999>, e.g.
results/win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261124_234

Environments (chosen automatically from the processor architecture; override with --envs):
  x64       python.org CPython x64 + win_amd64 wheels (native on Intel/AMD, emulated on ARM64)
  arm64     python.org CPython ARM64 + win_arm64 wheels (ARM64 only; some wheels are built locally, see README)
  arm64ec   ARM64EC CPython build + win_amd64 wheels (ARM64 only, optional: --arm64ec-python or ARM64EC_PYTHON)

Run options: --sections, --envs, --threads, --results, --cooldown, --idle, --idle-load, --repeats, --tasks,
--no-rerun.
See README.md.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENVDIR = ROOT / ".envs"
PY_VERSION = "3.12.10"
NUGET_PACKAGE = {"x64": "python", "arm64": "pythonarm64"}
TORCH_INDEX = "https://download.pytorch.org/whl/cpu"
ALL_ENVS = ["x64", "arm64ec", "arm64"]
# requirements.lock lines replaced for arm64: the VTK wheel built from the v9.7.2 source tree is versioned 9.7.2.dev0
ARM64_OVERRIDES = {"vtk==9.7.2": "vtk==9.7.2.dev0"}
ALL_SECTIONS = ["startup", "io", "numpy", "cpp", "render", "ai", "onnx"]
ALL_THREADS_ONLY = {"io", "ai", "onnx"}  # sections run only with all threads
LOAD_MEAN_LIMIT, LOAD_MAX_LIMIT = 4.0, 20.0  # % of machine; runs above are repeated once (see loadmon.py)


# ----------------------------------------------------------------------------------------------- helpers

def host_arch():
    """Native processor architecture (platform.machine() reports the native one also under x64 emulation)."""
    return "arm64" if platform.machine().upper() in ("ARM64", "AARCH64") else "x64"


def computer_name():
    return platform.node() or "computer"


_computer_id = None


def computer_id():
    """Compact hardware description (bench/sysinfo.py), e.g. win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_..."""
    global _computer_id
    if _computer_id is None:
        from bench import sysinfo
        _computer_id = sysinfo.short_id()
    return _computer_id


def new_results_dir():
    """results/<computer id>_<YYYYMMDD>_<time of day scaled to 000-999 (1 unit = 86.4 s)>"""
    t = time.localtime()
    day_fraction = (t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec) * 1000 // 86400
    return ROOT / "results" / f"{computer_id()}_{time.strftime('%Y%m%d', t)}_{day_fraction:03d}"


def latest_results_dir():
    """Newest results folder of this computer (also the old results/<computer name> naming)."""
    pattern = re.compile(re.escape(computer_id()) + r"_\d{8}_\d{3}")  # not an id that only starts with this one
    dirs = [d for d in (ROOT / "results").glob(f"{computer_id()}_*") if d.is_dir() and pattern.fullmatch(d.name)]
    if dirs:
        return max(dirs, key=lambda d: d.name.rsplit("_", 2)[-2:])  # by date, then time of day
    legacy = ROOT / "results" / computer_name()
    if legacy.is_dir():
        return legacy
    raise SystemExit(f"No results of this computer in results/{computer_id()}_*: run 'python benchmark.py run' "
                     "first, or give the folder with --results.")


def env_python(name):
    return ENVDIR / name / "Scripts" / "python.exe"


def tools_python():
    return env_python("tools")


def log(msg, logfile=None):
    line = f"=== {time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    if logfile:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def run(cmd, logfile=None, check=True, env=None):
    """Run a command; output goes to the console, or appended to logfile."""
    cmd = [str(c) for c in cmd]
    e = dict(os.environ, PYTHONIOENCODING="utf-8", **(env or {}))
    if logfile:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write("$ " + " ".join(cmd) + "\n")
            f.flush()
            r = subprocess.run(cmd, cwd=ROOT, env=e, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    else:
        r = subprocess.run(cmd, cwd=ROOT, env=e)
    if check and r.returncode != 0:
        raise SystemExit(f"Command failed ({r.returncode}): {' '.join(cmd)}")
    return r.returncode


def lock_hash(*files):
    h = hashlib.sha256()
    for f in files:
        h.update((ROOT / f).read_bytes() if (ROOT / f).exists() else b"")
    return h.hexdigest()[:16]


# ----------------------------------------------------------------------------------------------- setup

def nuget_python(arch):
    """python.org CPython from NuGet (no installer, no admin rights, nothing registered)."""
    pkg = NUGET_PACKAGE[arch]
    exe = ENVDIR / f"nuget-{pkg}" / "tools" / "python.exe"
    if not exe.exists():
        dl = ENVDIR / "dl"
        dl.mkdir(parents=True, exist_ok=True)
        nupkg = dl / f"{pkg}.{PY_VERSION}.nupkg"
        url = f"https://www.nuget.org/api/v2/package/{pkg}/{PY_VERSION}"
        log(f"downloading {url}")
        urllib.request.urlretrieve(url, nupkg)
        with zipfile.ZipFile(nupkg) as z:
            z.extractall(ENVDIR / f"nuget-{pkg}")
    return exe


def arm64ec_python(args):
    p = getattr(args, "arm64ec_python", None) or os.environ.get("ARM64EC_PYTHON")
    return Path(p) if p and Path(p).exists() else None


def base_python(name, args):
    return arm64ec_python(args) if name == "arm64ec" else nuget_python(name)


def default_envs(args):
    if host_arch() == "x64":
        return ["x64"]
    return ["x64"] + (["arm64ec"] if arm64ec_python(args) else []) + ["arm64"]


def is_ready(name):
    return (ENVDIR / name / "setup-done.txt").exists()


def create_venv(name, base):
    if not env_python(name).exists():
        log(f"creating virtual environment .envs/{name} from {base}")
        run([base, "-m", "venv", ENVDIR / name])
    run([env_python(name), "-m", "pip", "install", "-q", "--disable-pip-version-check", "pip==26.3"])


def setup_tools():
    """Helper environment (x64) for data download, load monitoring and reports; not benchmarked."""
    marker = ENVDIR / "tools" / "setup-done.txt"
    h = lock_hash("requirements-tools.txt")
    if marker.exists() and marker.read_text().strip() == h:
        return
    create_venv("tools", nuget_python("x64"))
    run([tools_python(), "-m", "pip", "install", "-q", "-r", ROOT / "requirements-tools.txt"])
    marker.write_text(h)


def setup_env(name, args):
    files = ["requirements.lock"] + (["requirements-npu.txt"] if name == "arm64" else [])
    marker = ENVDIR / name / "setup-done.txt"
    h = lock_hash(*files)
    if marker.exists() and marker.read_text().strip() == h:
        log(f"environment {name} is up to date")
        return True
    base = base_python(name, args)
    if base is None:
        log(f"skipping {name}: no ARM64EC Python (use --arm64ec-python or set ARM64EC_PYTHON)")
        return False
    create_venv(name, base)
    py = env_python(name)
    wheels = Path(args.wheels).resolve()
    req = ENVDIR / name / "requirements.used.txt"
    lines = (ROOT / "requirements.lock").read_text().splitlines()
    if name == "arm64":
        lines = [ARM64_OVERRIDES.get(x.strip(), x) for x in lines]
    req.write_text("\n".join(lines) + "\n")
    # Exactly the locked set (--no-deps). win_arm64 wheels that are not on PyPI are taken from --wheels.
    rc = run([py, "-m", "pip", "install", "-q", "--disable-pip-version-check", "--no-deps", "--find-links", wheels,
              "--extra-index-url", TORCH_INDEX, "-r", req], check=False)
    if rc != 0:
        msg = f"package installation failed for {name}."
        if name == "arm64":
            msg += (f" win_arm64 wheels of SimpleITK, VTK, connected-components-3d and ndindex are not on PyPI: copy "
                    f"them to {wheels} from another computer, or build them (scripts/build-arm64-wheels/, README).")
        log("ERROR: " + msg)
        return False
    # torchvision (imported by timm/nnU-Net): PyPI has no win_arm64 wheel; the PyTorch index has 0.29.1a0 for arm64
    if name == "arm64":
        run([py, "-m", "pip", "install", "-q", "--no-deps", "--index-url", TORCH_INDEX, "torchvision==0.29.1a0+cpu"])
        run([py, "-m", "pip", "install", "-q", "--no-deps", "-r", ROOT / "requirements-npu.txt"])
    else:
        run([py, "-m", "pip", "install", "-q", "--no-deps", "torchvision==0.29.1"])
    run([py, "-c", "import sys, sysconfig, platform; print(sys.executable, sys.version.split()[0], "
                   "sysconfig.get_platform(), platform.machine())"])
    marker.write_text(h)
    return True


def cmd_setup(args):
    if os.name != "nt":
        raise SystemExit("This benchmark runs on Windows only.")
    setup_tools()
    envs = args.envs.split(",") if args.envs else default_envs(args)
    ok = [e for e in envs if setup_env(e, args)]
    log(f"environments ready: {', '.join(ok) or 'none'} (host architecture: {host_arch()})")


# ----------------------------------------------------------------------------------------------- data

def onnx_models():
    d = ROOT / "data" / "models" / "onnx"
    return [f for f in d.glob("*.onnx") if not f.stem.endswith(("-static", "_ctx"))] if d.exists() else []


def cmd_data(args):
    setup_tools()
    if not is_ready("x64"):
        raise SystemExit("Run 'python benchmark.py setup' first (the x64 environment is used to prepare data).")
    x64 = env_python("x64")
    log("test data: 20 CT series from NCI Imaging Data Commons (manifest/idc_series.csv, ~2.2 GB)")
    run([tools_python(), "scripts/download_idc.py"])
    if not all((ROOT / "data" / "nrrd" / f"{c}.nrrd").exists() for c in case_ids()):
        log("converting DICOM to NRRD and NIfTI (bench.prepare)")
        run([x64, "-m", "bench.prepare"])
    log("AI models (TotalSegmentator, MONAIAuto3DSeg)")
    run([x64, "scripts/download_models.py"])
    if not onnx_models():
        log("exporting the MONAI network to ONNX (installs torch and monai in the tools environment)")
        run([tools_python(), "-m", "pip", "install", "-q", "-r", ROOT / "requirements-export.txt"])
        run([tools_python(), "scripts/export_onnx.py"])
    for f in onnx_models():
        static = f.with_name(f.stem + "-static.onnx")
        if not static.exists():
            run([tools_python(), "scripts/make_static_onnx.py", f, static])
    if host_arch() == "arm64" and is_ready("arm64"):
        ctx = list((ROOT / "data" / "models" / "onnx").glob("*_ctx.onnx"))
        if not ctx:
            log("compiling the NPU (QNN) context model; takes about 15-20 minutes, once")
            if run([env_python("arm64"), "scripts/npu_probe.py", "--make-context"], check=False) != 0:
                log("no NPU context model: the NPU tasks of section 6 will be skipped")
        if list((ROOT / "data" / "models" / "onnx").glob("*_ctx.onnx")):
            prepare_totalseg_npu()
    log("data ready")


def prepare_totalseg_npu():
    """Task 6c: export the 5 TotalSegmentator full-resolution networks to ONNX and compile them for the NPU."""
    d = ROOT / "data" / "models" / "onnx" / "totalseg"
    if len(list(d.glob("*_ctx.onnx"))) >= 5:
        return
    if len([f for f in d.glob("*.onnx") if not f.stem.endswith("_ctx")]) < 5:
        log("exporting the TotalSegmentator full-resolution networks to ONNX (arm64 environment + onnx add-on)")
        addon = ROOT / ".envs" / "onnx-addon-arm64"
        run([env_python("arm64"), "-m", "pip", "install", "-q", "--no-deps", "--target", addon, "-r",
             ROOT / "requirements-export-arm64.txt"])
        if run([env_python("arm64"), "scripts/export_totalseg_onnx.py"], check=False,
               env={"PYTHONPATH": str(addon)}) != 0:
            log("TotalSegmentator ONNX export failed: task 6c will be skipped")
            return
    log("compiling the 5 TotalSegmentator networks for the NPU; about 35 minutes each, several in parallel "
        "(as many as fit in the free memory, 5 GB each), once")
    if run([env_python("arm64"), "scripts/totalseg_npu.py", "compile"], check=False) != 0:
        log("not all TotalSegmentator NPU models were compiled: task 6c will be skipped")


def case_ids():
    import csv
    with (ROOT / "manifest" / "idc_series.csv").open() as f:
        return [r["case_id"] for r in csv.DictReader(f)]


# ----------------------------------------------------------------------------------------------- run

class LoadMonitor:
    """Logs CPU load of other processes to <results>/load.log during the run (scripts/loadmon.py)."""

    def __init__(self, results):
        self.file = results / "load.log"
        self.proc = subprocess.Popen([str(tools_python()), "scripts/loadmon.py", "log", str(self.file)], cwd=ROOT,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self):
        # the venv launcher starts the real interpreter as a child process; stop that one by its PID file
        pidfile = Path(str(self.file) + ".pid")
        if pidfile.exists():
            subprocess.run(["taskkill", "/F", "/PID", pidfile.read_text().strip()], capture_output=True)
            pidfile.unlink()
        self.proc.kill()


def latest_results(results):
    found = {}
    for f in sorted(results.glob("*/*.json")):
        try:
            d = json.loads(f.read_text())
        except (ValueError, OSError):
            continue
        if "start_epoch" in d and not d.get("task_filter"):  # partial runs (--tasks) add to a full run
            found[(d["environment"]["env"], d["section"], d["threads"])] = d
    return found


def annotate_load(results):
    """Store the CPU load of other processes during each run in its result file ("foreign_load": mean and max % of
    the machine, from load.log). Only numbers: process names stay in the local load.log, which is not published."""
    rows = []
    f = results / "load.log"
    if f.exists():
        for line in f.read_text().splitlines():
            p = line.split(" ")
            if len(p) >= 3:
                rows.append((float(p[0]), float(p[2])))
    for jf in sorted(results.glob("*/*.json")):
        try:
            d = json.loads(jf.read_text())
        except (ValueError, OSError):
            continue
        if "start_epoch" not in d:
            continue
        vals = [v for t, v in rows if d["start_epoch"] <= t <= d["end_epoch"] + 5]
        if vals:
            load = {"mean": round(sum(vals) / len(vals), 1), "max": max(vals), "samples": len(vals)}
            if d.get("foreign_load") != load:
                d["foreign_load"] = load
                jf.write_text(json.dumps(d, indent=1))


def overlapped_load(results):
    """(env, section, threads) of the latest runs during which other processes used too much CPU."""
    annotate_load(results)
    return [key for key, d in sorted(latest_results(results).items()) if d.get("foreign_load") and (
        d["foreign_load"]["mean"] >= LOAD_MEAN_LIMIT or d["foreign_load"]["max"] >= LOAD_MAX_LIMIT)]


def cmd_run(args):
    envs = [e for e in (args.envs.split(",") if args.envs else default_envs(args)) if is_ready(e)]
    if not envs:
        raise SystemExit("No environment is set up: run 'python benchmark.py setup' first.")
    if not (ROOT / "data" / "nrrd").exists():
        raise SystemExit("No test data: run 'python benchmark.py data' first.")
    sections = args.sections.split(",") if args.sections else ALL_SECTIONS
    ncpu = os.cpu_count()
    threads = sorted({ncpu if t == "all" else int(t) for t in args.threads.split(",")})
    results = Path(args.results).resolve() if args.results else new_results_dir()
    args.results = str(results)  # the report at the end uses the same folder
    results.mkdir(parents=True, exist_ok=True)
    logfile = results / f"run-{time.strftime('%Y%m%d-%H%M%S')}.log"
    benv = {"BENCH_RESULTS": str(results)}
    log(f"computer {computer_id()}, host {host_arch()}, {ncpu} logical CPUs; environments {envs}; "
        f"sections {sections}; threads {threads}; results {results}; log {logfile}", logfile)

    def one(env, section, t):
        time.sleep(args.cooldown)
        run([tools_python(), "scripts/loadmon.py", "wait", args.idle, args.idle_load], logfile, check=False)
        log(f"{env} {section} threads={t}", logfile)
        cmd = [env_python(env), "-m", "bench.run", section, "--env", env, "--threads", t]
        if args.repeats is not None:
            cmd += ["--repeats", args.repeats]
        if args.tasks:
            cmd += ["--tasks", args.tasks]
        if run(cmd, logfile, check=False, env=benv) != 0:
            log(f"FAILED: {env} {section} threads={t} (see {logfile.name})", logfile)

    mon = LoadMonitor(results)
    try:
        for section in sections:
            if section == "startup":
                run([tools_python(), "scripts/loadmon.py", "wait", args.idle, args.idle_load], logfile,
                    check=False)
                log("startup", logfile)
                run([tools_python(), "-m", "bench.startup", *envs], logfile, check=False, env=benv)
                continue
            for t in ([ncpu] if section in ALL_THREADS_ONLY else threads):
                for env in envs:
                    one(env, section, t)
        if not args.no_rerun:
            # Repeat (once) runs that overlapped CPU load from other processes; AI runs take too long to repeat
            for env, section, t in overlapped_load(results):
                if section in sections and section not in ("ai", "startup") and env in envs:
                    log(f"repeating {env} {section} threads={t}: other processes used the CPU during the run",
                        logfile)
                    one(env, section, t)
        if "extra" not in (args.skip or ""):
            log("extra checks (SVD thread scaling, zlib)", logfile)
            run([tools_python(), "-m", "bench.extra_checks", *envs], logfile, check=False, env=benv)
    finally:
        mon.stop()
    remaining = overlapped_load(results)
    if remaining:
        log("runs that still overlapped load from other processes: " + ", ".join(
            f"{e} {s} t{t}" for e, s, t in remaining), logfile)
    log("benchmark finished", logfile)
    cmd_report(args)


# ----------------------------------------------------------------------------------------------- report

def cmd_report(args):
    setup_tools()
    results = Path(args.results).resolve() if args.results else latest_results_dir()
    out = Path(args.report_dir).resolve() if args.report_dir else ROOT / "reports" / results.name
    run([tools_python(), "scripts/compare.py", results])
    cmd = [tools_python(), "scripts/make_report.py", results, "--out", out]
    if args.replicate:
        cmd += ["--replicate", Path(args.replicate).resolve()]
    run(cmd)
    if results.parent == ROOT / "results":
        run([tools_python(), "scripts/collect_results.py"])  # results/all.csv and results/README.md
    run([tools_python(), "scripts/check_privacy.py", results], check=False)
    log(f"report: {out / 'report.html'}")


def cmd_all(args):
    cmd_setup(args)
    cmd_data(args)
    cmd_run(args)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["setup", "data", "run", "report", "all"])
    p.add_argument("--envs", help="comma-separated, e.g. x64,arm64 (default: all that apply to this computer)")
    p.add_argument("--arm64ec-python", help="python.exe of an ARM64EC CPython 3.12 build (optional)")
    p.add_argument("--wheels", default=str(ROOT / "wheels" / "arm64"), help="folder with locally built win_arm64 "
                   "wheels (default: wheels/arm64)")
    p.add_argument("--sections", help=f"comma-separated subset of {','.join(ALL_SECTIONS)} (default: all)")
    p.add_argument("--threads", default="1,all", help="thread counts for numpy, cpp and render (default: 1,all)")
    p.add_argument("--results", help="results folder (default for run: a new results/<computer id>_<date>_<time "
                   "of day as 000-999>, e.g. results/win_arm64_cpu_..._npu_hexagon_20261124_234; default for "
                   "report: the newest results folder of this computer)")
    p.add_argument("--report-dir", help="report folder (default: reports/<results folder name>)")
    p.add_argument("--replicate", help="results folder of an earlier run, compared in the report")
    p.add_argument("--cooldown", type=int, default=60, help="seconds of rest before each run (default: 60)")
    p.add_argument("--idle", type=int, default=30, help="seconds without load from other processes required "
                   "before each run (default: 30)")
    p.add_argument("--idle-load", type=float, default=6.0, help="CPU load of other processes (%% of the machine) "
                   "below which the computer counts as idle before each run (default: 6)")
    p.add_argument("--repeats", type=int, help="timed repeats per task (default: per section)")
    p.add_argument("--tasks", help="comma-separated task groups, e.g. 2a,3e (default: all tasks)")
    p.add_argument("--no-rerun", action="store_true", help="do not repeat runs that overlapped other CPU load")
    p.add_argument("--skip", help="'extra' to skip the extra checks")
    args = p.parse_args()
    {"setup": cmd_setup, "data": cmd_data, "run": cmd_run, "report": cmd_report, "all": cmd_all}[args.command](args)


if __name__ == "__main__":
    main()
