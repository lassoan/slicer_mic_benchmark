"""Measure interpreter startup and import time of each environment (run from any Python).

The first run after the environment has been idle is reported separately ("first"); it includes Prism
translation for emulated code if the translation cache is cold. The median is over 5 further runs.

Usage: python -m bench.startup x64 arm64ec arm64
"""

import json
import statistics
import subprocess
import sys
import time

from bench import config

COMMANDS = {
    "python_startup": "pass",
    "import_numpy_scipy": "import numpy, scipy.ndimage, scipy.linalg",
    "import_simpleitk": "import SimpleITK",
    "import_vtk_all": "import vtk",
    "import_torch": "import torch",
    "import_bench_stack": "import numpy, scipy.ndimage, SimpleITK, nibabel, nrrd, pydicom, vtk",
}
REPEATS = 5


def main():
    envs = sys.argv[1:] or ["x64", "arm64ec", "arm64"]
    for env in envs:
        exe = config.ROOT / ".envs" / env / "Scripts" / "python.exe"
        results = {}
        for name, code in COMMANDS.items():
            times = []
            for _ in range(REPEATS + 1):
                t0 = time.perf_counter()
                subprocess.run([str(exe), "-c", code], check=True, capture_output=True)
                times.append(time.perf_counter() - t0)
            results[name] = {"first_s": times[0], "median_s": statistics.median(times[1:]), "times_s": times[1:],
                             "signature": None}
            print(f"[{env}] {name:24s} first {times[0]:.3f} s  median {results[name]['median_s']:.3f} s", flush=True)
        out = config.RESULTS_DIR / env / f"{time.strftime('%Y%m%d-%H%M%S')}-startup-t0.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"section": "startup", "threads": 0, "environment": {"env": env},
                                   "tasks": results}, indent=1))


if __name__ == "__main__":
    main()
