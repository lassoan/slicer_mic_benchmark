"""Background CPU load from processes that are not part of the benchmark.

  python scripts/loadmon.py log <file>      sample every 5 s, append "epoch total% foreign% top-foreign-processes"
  python scripts/loadmon.py wait [secs]     return when foreign load < 6% of the machine for <secs> (default 30) s

"Foreign" = all processes except benchmark runs (bench.run, bench.startup, bench.extra_checks), the driver
(benchmark.py) and this monitor, and their children. Percentages are of the whole machine (all logical CPUs = 100%).
"""

import sys
import time

import psutil

NCPU = psutil.cpu_count()


def bench_pids():
    pids = set()
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = " ".join(a or "" for a in (p.info["cmdline"] or []))
            # benchmark runs, the run script and this monitor; anything else (also other scripts in this
            # repository) counts as foreign load
            if any(k in cmd for k in ("bench.run", "bench.startup", "bench.extra_checks", "loadmon.py", "benchmark.py")):
                pids.add(p.info["pid"])
                pids.update(c.pid for c in p.children(recursive=True))
        except (psutil.Error, OSError):
            pass
    pids.add(psutil.Process().pid)
    return pids


def sample(interval):
    procs = {}
    for p in psutil.process_iter():
        try:
            p.cpu_percent(None)
            procs[p.pid] = p
        except psutil.Error:
            pass
    total = psutil.cpu_percent(interval=interval)
    ours = bench_pids()
    foreign = []
    for pid, p in procs.items():
        if pid in ours or pid == 0:
            continue
        try:
            c = p.cpu_percent(None) / NCPU
            name = p.name() if c > 0 else ""
        except psutil.Error:
            continue
        if c > 0:
            foreign.append((c, name))
    foreign.sort(reverse=True)
    return total, sum(c for c, _ in foreign), foreign[:3]


def main():
    mode = sys.argv[1]
    if mode == "log":
        import os
        with open(sys.argv[2] + ".pid", "w") as f:
            f.write(str(os.getpid()))
        with open(sys.argv[2], "a", buffering=1) as f:
            while True:
                total, fl, top = sample(5)
                f.write(f"{time.time():.0f} {total:.1f} {fl:.1f} " + ",".join(f"{n}:{c:.1f}" for c, n in top) + "\n")
    elif mode == "wait":
        need = float(sys.argv[2]) if len(sys.argv) > 2 else 30
        quiet_since = time.time()
        while True:
            _, fl, top = sample(5)
            if fl >= 6.0:
                quiet_since = time.time()
                print(f"waiting: foreign load {fl:.1f}% {top}", flush=True)
            elif time.time() - quiet_since >= need:
                return


if __name__ == "__main__":
    main()
