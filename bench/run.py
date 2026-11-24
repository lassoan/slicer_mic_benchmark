"""Run one benchmark section in one environment.

Usage: python -m bench.run <section> --env <name> --threads <n> [--repeats N] [--cases case01,case02]
Sections: io, numpy, cpp, render, ai, onnx (startup: bench/startup.py)
"""

import argparse
import importlib
import os
import sys
import time
from pathlib import Path

SECTIONS = {"io": "t1_io", "numpy": "t2_numpy", "cpp": "t3_cpp", "render": "t4_render", "ai": "t5_ai", "onnx": "t6_onnx"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("section", choices=list(SECTIONS))
    p.add_argument("--env", required=True)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--repeats", type=int, default=None)
    p.add_argument("--warmup", type=int, default=1)
    p.add_argument("--cases", default=None, help="comma-separated case ids (default: section default)")
    p.add_argument("--tasks", default=None, help="comma-separated task name prefixes to run (default: all)")
    p.add_argument("--out", default=None)
    args = p.parse_args()

    os.environ["BENCH_ENV"] = args.env
    # Thread environment variables must be set before importing numpy, SimpleITK, VTK or torch
    from bench import harness
    harness.set_thread_env(args.threads)

    mod = importlib.import_module(f"bench.{SECTIONS[args.section]}")
    cases = args.cases.split(",") if args.cases else None
    tasks = args.tasks.split(",") if args.tasks else None
    repeats = args.repeats if args.repeats is not None else mod.DEFAULT_REPEATS
    runner = harness.Runner(args.section, args.threads, repeats, args.warmup)
    print(f"[{args.env}] section {args.section}, threads {args.threads}, repeats {repeats}", flush=True)
    start_epoch = time.time()
    t0 = time.perf_counter()
    extra = mod.run(runner, cases=cases, tasks=tasks, threads=args.threads, env=args.env) or {}
    extra["section_wall_time_s"] = time.perf_counter() - t0
    extra["start_epoch"] = start_epoch
    extra["end_epoch"] = time.time()
    extra["library_threads"] = harness.set_library_threads(args.threads)
    from bench import config
    out = args.out or (config.RESULTS_DIR / args.env /
                       f"{time.strftime('%Y%m%d-%H%M%S')}-{args.section}-t{args.threads}.json")
    runner.save(out, extra)


if __name__ == "__main__":
    sys.exit(main())
