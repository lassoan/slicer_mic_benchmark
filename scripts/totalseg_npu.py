"""Compile and probe the TotalSegmentator full-resolution networks on the Snapdragon Hexagon NPU (task 6c,
bench/totalseg_npu.py). Run in the arm64 environment, after scripts/export_totalseg_onnx.py.

Usage:
  python scripts/totalseg_npu.py compile [--jobs N] [291 292 ...]
      compile the EP context models that do not exist yet (about 35 min and 5 GB of memory per model; N models in
      parallel, default: as many as fit in the available memory, at most 5)
  python scripts/totalseg_npu.py patch
      time one 128^3 patch per model on the NPU and with ONNX Runtime on the CPU, and compare the outputs
"""

import ctypes
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402

from bench.totalseg_npu import TASK_IDS, ctx_file, onnx_file  # noqa: E402

GB_PER_JOB = 6  # peak working set of one compile is about 5 GB


def available_memory_gb():
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + \
                   [(n, ctypes.c_ulonglong) for n in ("total", "avail", "tp", "ap", "tv", "av", "aev")]
    m = MEMORYSTATUSEX()
    m.dwLength = ctypes.sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.avail / 2**30


def compile_one(tid):
    from npu_probe import npu_session
    t0 = time.perf_counter()
    npu_session(cache=ctx_file(tid), model=onnx_file(tid))
    print(f"Dataset{tid}: context model written in {time.perf_counter() - t0:.0f} s "
          f"({ctx_file(tid).stat().st_size / 1e6:.0f} MB)", flush=True)


def compile_models(tids, jobs):
    """One process per model, at most `jobs` at a time (compiling uses about one CPU core per model)."""
    todo = [t for t in tids if not ctx_file(t).exists()]
    if len(todo) == 1:
        return compile_one(todo[0])
    running, failed = [], []
    while todo or running:
        while todo and len(running) < jobs:
            t = todo.pop(0)
            print(f"Dataset{t}: compiling", flush=True)
            running.append((t, subprocess.Popen([sys.executable, __file__, "compile", str(t)],
                                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)))
        time.sleep(10)
        for t, p in list(running):
            if p.poll() is not None:
                running.remove((t, p))
                ok = p.returncode == 0 and ctx_file(t).exists()
                print(f"Dataset{t}: {'done' if ok else f'failed ({p.returncode})'}", flush=True)
                if not ok:
                    failed.append(t)
    if failed:
        raise SystemExit(f"compiling failed for {failed}")


def patch_times():
    import onnxruntime as ort
    from npu_probe import npu_session
    x = np.random.default_rng(0).standard_normal((1, 1, 128, 128, 128), dtype=np.float32)
    for tid in TASK_IDS:
        if not ctx_file(tid).exists():
            continue
        t0 = time.perf_counter()
        sess = npu_session(model=ctx_file(tid))
        load = time.perf_counter() - t0
        sess.run(None, {"input": x})
        ts = []
        for _ in range(5):
            t0 = time.perf_counter()
            y = sess.run(None, {"input": x})[0]
            ts.append(time.perf_counter() - t0)
        cpu = ort.InferenceSession(str(onnx_file(tid)), providers=["CPUExecutionProvider"])
        t0 = time.perf_counter()
        ref = cpu.run(None, {"input": x})[0]
        tc = time.perf_counter() - t0
        print(f"Dataset{tid}: load {load:.1f} s, NPU patch median {np.median(ts):.3f} s, ORT CPU patch {tc:.2f} s, "
              f"max abs diff {np.abs(y - ref).max():.3f}, argmax agreement {(y.argmax(1) == ref.argmax(1)).mean():.5f}",
              flush=True)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "compile":
        jobs = max(1, min(len(TASK_IDS), int(available_memory_gb() // GB_PER_JOB)))
        if "--jobs" in args:
            i = args.index("--jobs")
            jobs = int(args[i + 1])
            del args[i:i + 2]
        compile_models([int(a) for a in args] or TASK_IDS, jobs)
    elif cmd == "patch":
        patch_times()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
