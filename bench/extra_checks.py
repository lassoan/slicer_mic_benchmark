"""Targeted checks of suspicious results (run from any Python):

- SVD thread scaling: numpy.linalg.svd of 2000x2000 with 1, 2, 4, 8, ... and all logical CPUs as BLAS threads (new process per thread count,
  thread environment variables set before numpy is imported), median of 5 after one warm-up.
- zlib: compress 64 MB of CT voxels (case01) at level 1 and decompress; reports zlib version.

Usage: python -m bench.extra_checks [envs...]   -> <BENCH_RESULTS>/extra_checks.json
"""

import json
import os
import subprocess
import sys

from bench import config

SVD_CODE = r"""
import time, statistics, numpy as np
m = np.random.default_rng(42).standard_normal((2000, 2000))
np.linalg.svd(m)
t = []
for _ in range(5):
    t0 = time.perf_counter(); np.linalg.svd(m); t.append(time.perf_counter() - t0)
print(statistics.median(t))
"""

ZLIB_CODE = r"""
import time, statistics, zlib, nrrd, numpy as np
d = nrrd.read(r'{nrrd}')[0].tobytes()[:64 * 2**20]
c = zlib.compress(d, 1)
tc, td = [], []
for _ in range(5):
    t0 = time.perf_counter(); c = zlib.compress(d, 1); tc.append(time.perf_counter() - t0)
    t0 = time.perf_counter(); zlib.decompress(c); td.append(time.perf_counter() - t0)
print(zlib.ZLIB_RUNTIME_VERSION, statistics.median(tc), statistics.median(td), len(c) / len(d))
"""


def main():
    envs = sys.argv[1:] or ["x64", "arm64ec", "arm64"]
    out = {}
    for env in envs:
        exe = str(config.ROOT / ".envs" / env / "Scripts" / "python.exe")
        res = {"svd_2000_s": {}}
        ncpu = os.cpu_count()
        for n in sorted({2 ** i for i in range(8) if 2 ** i < ncpu} | {ncpu}):
            e = dict(os.environ, OMP_NUM_THREADS=str(n), OPENBLAS_NUM_THREADS=str(n), MKL_NUM_THREADS=str(n))
            t = float(subprocess.run([exe, "-c", SVD_CODE], env=e, capture_output=True, text=True, check=True).stdout)
            res["svd_2000_s"][n] = round(t, 3)
        z = subprocess.run([exe, "-c", ZLIB_CODE.format(nrrd=config.NRRD_DIR / "case01.nrrd")], capture_output=True,
                           text=True, check=True).stdout.split()
        res["zlib"] = {"version": z[0], "compress_64MB_s": round(float(z[1]), 3),
                       "decompress_64MB_s": round(float(z[2]), 3), "ratio": round(float(z[3]), 3)}
        out[env] = res
        print(env, json.dumps(res), flush=True)
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.RESULTS_DIR / "extra_checks.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
