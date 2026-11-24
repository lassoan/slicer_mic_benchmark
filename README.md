# Medical image computing benchmark: Python on Windows (x64 and ARM64)

Times typical medical image computing workloads in Python (DICOM and file I/O, numpy/scipy, ITK and VTK
algorithms, VTK rendering, AI segmentation with PyTorch and ONNX Runtime, and the NPU where there is one) and
writes a report. On an ARM64 computer it compares up to three builds of CPython 3.12.10:

| Environment | Interpreter | Packages | Emulated on ARM64 | Available on |
| --- | --- | --- | --- | --- |
| `x64` | python.org x64 | `win_amd64` wheels | everything | all computers (native on Intel/AMD) |
| `arm64ec` | ARM64EC build (optional, see below) | the same `win_amd64` wheels | extension modules only | ARM64 |
| `arm64` | python.org ARM64 | `win_arm64` wheels (some built locally) | nothing | ARM64 |

On an Intel/AMD computer only `x64` runs, so the report has absolute times (for comparing computers) instead of
speed-ups. See [PLAN.md](PLAN.md) for the design and task parameters.

## Running the benchmark

Requirements: Windows 10/11 (x64 or ARM64), any Python 3.9+ to start the driver (python.org or `py`), internet
access, about 15 GB of free disk space, and 4–8 hours. No administrator rights are needed: the driver downloads
its own Python interpreters (python.org NuGet packages) into `.envs/`.

```bat
git clone <this repository> mic-benchmark-py
cd mic-benchmark-py
python benchmark.py all
```

`all` runs these steps, which can also be run one at a time:

| Command | What it does | Time |
| --- | --- | --- |
| `python benchmark.py setup` | Downloads CPython 3.12.10 (x64; ARM64 on ARM64 computers) and creates the virtual environments in `.envs/`: `tools` (helper, not timed) and one per benchmark environment, with exactly the versions in [requirements.lock](requirements.lock) | 5–15 min |
| `python benchmark.py data` | Downloads the 20 CT series listed in [manifest/idc_series.csv](manifest/idc_series.csv) from the NCI Imaging Data Commons (2.2 GB), converts them to NRRD/NIfTI, downloads the TotalSegmentator and MONAIAuto3DSeg models, exports the MONAI network to ONNX, and on a Snapdragon computer compiles the NPU model | 20–60 min |
| `python benchmark.py run` | Runs all sections in all environments (interleaved), repeats runs that overlapped CPU load from other programs, runs the extra checks, then writes the report | 3–7 h |
| `python benchmark.py report` | Rewrites the summary and the report from existing results | 1–3 min |

Each step skips work that is already done, so a step can be repeated after an error.

**Output:** each `run` writes to a new folder `<run>` = `<computer id>_<date>_<time of day as 000–999>` (one unit
is 86.4 s), for example
`win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261124_234`. The computer
id is a compact hardware description (`python bench/sysinfo.py --short`). `report` without `--results` uses the
newest folder of this computer.

- `results/<run>/<env>/*.json`: raw results (one file per section, thread count and environment), with
  machine, package and loaded-DLL architecture metadata. The computer description (OS, CPU cores and instruction
  set extensions, RAM type and speed, GPU, NPU, system disk, power source and mode) is in `environment.system`;
  `python bench/sysinfo.py` prints it for any computer (`--json` for all details; standard library only, also on
  Linux and macOS).
- `results/<run>/summary.md`: all tasks with times and speed-ups. Also in this folder:
  - `tasks.csv`: one row per task, environment and thread count (machine-readable)
  - `summary.json`: the same as `summary.md`, plus the output checks
  - `extra_checks.json`
  - local only, not in source control: `load.log` (CPU load and names of other programs during the run),
    `run-*.log` (console output), `<env>/images/` (rendered frames, compared with x64 in `summary.json`)
- `results/all.csv` and `results/README.md`: every run combined (CSV) and an index of the runs, which GitHub
  shows when you open the [results](results/) folder.
- `reports/<run>/report.html` and `report.md`: the report, with machine and environments, automatically
  derived key findings, time per section, speed-ups, AI backends, extra checks and every task. The HTML file is
  self-contained (charts built in, light and dark mode). A hand-written `reports/<run>/findings.md`, if
  present, is included as notes. `reports/` is not in source control.

**Results website:** on every push that changes `results/`, a GitHub workflow
([.github/workflows/pages.yml](.github/workflows/pages.yml)) builds the reports of all runs with
`scripts/make_site.py` and publishes them on the repository's GitHub Pages site, with `all.csv` and each run's
`tasks.csv` and `summary.json`.

**Privacy:** results are meant to be published, so they contain no personal information:

- Paths are stored relative to `<repo>`, `<python>`, `<home>`, `<windows>` and similar roots, or as file names
  only.
- No computer or user names are stored.
- The load of other programs is stored as numbers only, without process names.

This is done by [bench/privacy.py](bench/privacy.py) when results are saved. `scripts/check_privacy.py` checks
the results at the end of `report` and in the GitHub workflow. Results written before this existed were cleaned
with `scripts/scrub_results.py`.

**Contributing results:** run the benchmark, then commit the new `results/<run>/` folder together with
`results/all.csv` and `results/README.md` in a pull request.

**For reliable timings:**

- Close other programs and keep the computer on AC power.
- Turn off sleep for the duration of the run.
- Don't use the computer during the run. The driver waits for an idle CPU before each run and logs and repeats
  runs disturbed by other processes, but it cannot remove the effect of thermal throttling or power-saving modes.

**Options for `run`:**

| Option | Default | Meaning |
| --- | --- | --- |
| `--envs x64,arm64` | all environments that apply to the computer | environments to run, in this order |
| `--sections io,cpp` | all sections | subset of `startup,io,numpy,cpp,render,ai,onnx` |
| `--threads 1,all` | `1,all` | thread counts for numpy, cpp and render; io, ai and onnx always use all threads |
| `--results DIR` | a new `results/<run>` | results folder (an existing one adds to it); the report goes to `reports/<folder name>` |
| `--replicate DIR` | | results of an earlier run, compared in the report |
| `--cooldown 60` | 60 | seconds of rest before each run |
| `--idle 30` | 30 | seconds of idle CPU, ignoring the benchmark, required before each run |
| `--repeats N` | per section | timed repeats per task |
| `--tasks 2a,3e` | all tasks | task groups |
| `--no-rerun` | off | don't repeat runs that overlapped load from other processes |
| `--skip extra` | off | skip the extra checks |

For a quick test of the setup (about 5 minutes):

```bat
python benchmark.py run --sections numpy --tasks 2a --threads 1 --repeats 1 --cooldown 0 --skip extra --results results/smoke-test
```

A single section in one environment, without the driver:

```bat
set BENCH_RESULTS=results\test
.envs\arm64\Scripts\python.exe -m bench.run cpp --env arm64 --threads 12
```

### ARM64 computers: locally built wheels

PyPI has no `win_arm64` wheels for SimpleITK 2.5.5, VTK 9.7.2, connected-components-3d 4.1.1 or ndindex 1.10.1.
`setup` installs them from `wheels/arm64/` (or `--wheels DIR`). Without them, `setup` reports the error and
continues with the other environments. There are two ways to get the wheels:

- **Copy** the folder `wheels/arm64` (65 MB) from a computer that has it. The wheels are built for any Windows ARM64
  computer.
- **Build** them. This needs Visual Studio 2026 with the ARM64 C++ tools, CMake, Git for Windows (bash) and about
  3 hours:

  ```bash
  PY=.envs/nuget-pythonarm64/tools/python.exe     # created by "benchmark.py setup"
  # SimpleITK (ITK superbuild, then scikit-build)
  scripts/build-arm64-wheels/build_simpleitk.sh $PY C:/build/sitk wheels/arm64 2.5.5
  # VTK: build from the v9.7.2 tag with VTK's wheel CI configuration, then add the DLLs to the wheel
  git clone --branch v9.7.2 --depth 1 https://gitlab.kitware.com/vtk/vtk.git C:/build/vtk-src
  cmd //c "scripts\build-arm64-wheels\build_vtk.bat .envs\nuget-pythonarm64\tools C:\build\vtk-src C:\build\vtk C:\build\vtk-wheel"
  #   unpack the wheel, run repack_vtk_wheel.py (see its docstring), pack it into wheels/arm64
  # small packages from source
  $PY -m pip wheel --no-deps connected-components-3d==4.1.1 ndindex==1.10.1 -w wheels/arm64
  ```

The `vtk==9.7.2` line in `requirements.lock` is mapped to the locally built `9.7.2.dev0` for arm64
(`ARM64_OVERRIDES` in [benchmark.py](benchmark.py)).

### ARM64 computers: the optional ARM64EC environment

There is no official ARM64EC build of CPython. The `arm64ec` environment needs a CPython 3.12 built for ARM64EC
(this one was built with python-cmake-buildsystem). Pass it with `--arm64ec-python <path to python.exe>` or the
`ARM64EC_PYTHON` environment variable. Without one, `arm64ec` is skipped.

### ARM64 computers: the NPU

On a Snapdragon X computer, the arm64 environment gets the `onnxruntime-qnn` plugin
([requirements-npu.txt](requirements-npu.txt)). `data` compiles the MONAI network for the Hexagon NPU once (about
17 minutes, 1.9 GB file in `data/models/onnx/`). If there is no NPU, or compiling fails, the NPU tasks are skipped.

## Results: Snapdragon X Elite laptop (2026-11-23/24)

Snapdragon X Elite X1E80100 (12 cores), 32 GB, Windows 11 build 26300, on AC power. All runs of all computers:
[results/](results/) and the results website.

**Where the data is:**

- [summary.md](results/win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261123_970/summary.md) (`results/…_20261123_970`): the main result, a full pass with CPU load
  from other processes logged and the runs that overlapped it repeated.
- [summary.md](results/win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261123_754/summary.md) (`results/…_20261123_754`): an earlier pass, used as a replicate.
- [replicates.md](results/win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261123_970/replicates.md): comparison of the two passes.

**Output:** in every section, every environment produced the same output as x64 (task checks, byte-identical
rendered images, segmentation Dice ≥ 0.9999). The one exception is section 6: in one case (case13), the ONNX
Runtime segmentation on arm64 has 0.4% fewer foreground voxels than on x64.

Speed-up compared with x64 under emulation (geometric mean of the tasks in each section; higher is better):

| Section | ARM64EC | native arm64 |
| --- | ---: | ---: |
| Python startup and imports | 1.08× | 1.43× |
| 1. File I/O and DICOM geometry (20 CTs) | 1.28×¹ | 1.39× |
| 2. numpy/scipy, 1 thread / 12 threads | 0.99× / 1.01× | 1.41× / 1.38× |
| 3. C++ (SimpleITK, VTK), 1 thread / 12 threads | 1.00× / 0.97× | 1.31× / 1.38× |
| 4. VTK rendering, 1 thread / 12 threads | 1.01× / 1.05× | 1.21× / 1.22× |
| 5. AI segmentation with PyTorch (CPU) | 1.01× | **0.27×** |
| 6. MONAI network with ONNX Runtime (CPU), per case vs ONNX Runtime on x64 | 1.01× | **1.5–2.0×** |

¹ Mostly from the gzip tasks (2.7–2.9×). This is not an architecture effect: the ARM64EC Python links zlib-ng,
which at level 1 compresses 2.8× faster but makes 38% larger files (compressed to 71% of the original size
instead of 51%). Without the gzip tasks, ARM64EC is close to 1.0×.

### Conclusions

- **Native arm64 is 1.2–1.45× faster than x64 emulation for everything except PyTorch.**
  - Largest gains:
    - pure Python: up to 1.8×
    - anisotropic diffusion: 1.7–2.2×
    - surface → label map stencil: 1.7×
    - FFT, `np.unique`, least-squares fit: about 2.2×
    - histograms and binary morphology: about 1.75×
  - About the same speed in every environment, so nothing gained on arm64:
    - GPU volume rendering, which goes through the same native OpenGL-on-D3D12 driver in every process
    - memory-bound scipy filters (Gaussian, median, distance transform)
- **ARM64EC gives practically no speed-up.**
  - The interpreter is native, but nearly all the time is spent in x64 extension modules (numpy, SimpleITK, VTK,
    PyTorch), which are still emulated.
  - It helps only pure-Python code (1.34× on the geometry check).
  - Its value is compatibility, not speed.
- **PyTorch on native arm64 is 3–7× slower than emulated x64 PyTorch.**
  - The `win_arm64` PyTorch 2.15 build has no oneDNN and uses only generic CPU code; the x64 build's MKL/oneDNN
    AVX2 kernels stay fast under emulation.
  - TotalSegmentator fast: about 100 s per case on arm64, against 31 s on x64.
  - TotalSegmentator full resolution: 51 minutes on arm64, against 7.8 minutes on x64.
- **The fix for AI is ONNX Runtime, and the NPU.** The same MONAIAuto3DSeg network, sliding-window inference per case:

  | Backend | case01 | case02 | case03 | case11 | case13 |
  | --- | ---: | ---: | ---: | ---: | ---: |
  | PyTorch, x64 (emulated), 12 threads | 15.9 s | 37.6 s | 37.7 s | 16.6 s | 17.5 s |
  | PyTorch, arm64, 12 threads | 91.9 s | 204.5 s | 203.9 s | 91.1 s | 91.7 s |
  | ONNX Runtime 1.32, x64 (emulated), 12 threads | 20.1 s | 43.1 s | 43.9 s | 20.6 s | 21.8 s |
  | ONNX Runtime 1.32, arm64, 12 threads | 11.0 s | 28.6 s | 28.1 s | 10.8 s | 10.9 s |
  | **ONNX Runtime + QNN on the Hexagon NPU (fp16)** | **3.2 s** | **6.9 s** | **6.9 s** | **3.4 s** | **3.1 s** |

  - **Speed:**
    - ONNX Runtime on the arm64 CPU is 7–8× faster than arm64 PyTorch, and 1.4–1.6× faster than the best x64
      result (PyTorch).
    - The NPU is 3.2–4.1× faster than the fastest CPU result (ONNX Runtime on arm64), 4.9–5.6× faster than x64
      PyTorch, and 27–30× faster than arm64 PyTorch.
  - **Agreement with the PyTorch label maps** (mean Dice over labels, per case):
    - ONNX Runtime: 0.9996–0.9997, except case13 at 0.9945
    - NPU: 0.9986–0.9998
  - **NPU setup:**
    - The whole network runs on the NPU, with no CPU fallback.
    - Compilation takes about 17 minutes, once, and is saved to a 1.9 GB "EP context" model that loads in 6 s.
    - The model needs fixed input shapes.
- **Other observations:**
  - **Linear algebra threading on arm64:** the arm64 OpenBLAS (numpy/scipy wheels) stops scaling at 4 threads.
    A 2000×2000 SVD takes 2.96 s with 1 thread and 2.06 s with 4 threads, but 2.27 s with 12 threads; x64 reaches
    1.48 s.
  - **zlib:** compression on native arm64 is 1.35× faster than on x64.

### Caveats

- **One machine.** Each value is the median of 3 timed repeats after a warm-up; the AI tasks have one run per
  case.
- **Load from other processes:**
  - During the first pass, another build ran on the same machine and slowed some runs, mainly AI by 20–40%.
  - The main pass waited for an idle machine before each run, logged outside load, and repeated the runs that
    overlapped it.
- **Package builds differ by platform:**
  - SimpleITK 2.5.5 everywhere, but the arm64 wheel is built with ITK 5.4.7 (official wheels: 5.4.5).
  - VTK 9.7.2 for arm64 is built from source.
  - torchvision 0.29.1 for x64 and ARM64EC, `0.29.1a0+cpu` for arm64.

## Sections

1. **File I/O and DICOM geometry** (20 abdominal CT series from IDC):
   - read headers (SimpleITK, pydicom)
   - check geometry in pure Python
   - read volumes (SimpleITK)
   - write and read NRRD (pynrrd) and NIfTI (nibabel)
2. **Vectorized Python** (numpy, scipy):
   - element-wise operations and reductions
   - ndimage filters
   - labeling and distance transform
   - resampling
   - linear algebra
   - FFT
3. **C++ algorithms**:
   - ITK: anisotropic diffusion, label map, label statistics, histogram
   - VTK: flying edges, windowed sinc smoothing, normals, surface back to label map with a stencil
4. **C++ visualization**: VTK surface rendering, GPU and CPU volume ray casting (offscreen, 1920x1080).
5. **AI segmentation on CPU**: TotalSegmentator (fast and full resolution) and MONAIAuto3DSeg.
6. **ONNX Runtime and NPU**: the MONAIAuto3DSeg network exported to ONNX. The same sliding-window inference runs
   with:
   - PyTorch
   - ONNX Runtime (CPU)
   - in arm64, ONNX Runtime with the QNN plugin on the Hexagon NPU

**Extra checks:** SVD thread scaling and zlib speed and compression ratio, in each environment.

## Repository layout

| Path | Content |
| --- | --- |
| [benchmark.py](benchmark.py) | driver: setup, data, run, report |
| [bench/](bench/) | benchmark sections (`t1_io.py` … `t6_onnx.py`), harness, configuration ([bench/config.py](bench/config.py)) |
| [scripts/](scripts/) | data and model download, ONNX export, NPU compilation, load monitor, summary and report |
| [scripts/build-arm64-wheels/](scripts/build-arm64-wheels/) | building the `win_arm64` wheels that are not on PyPI |
| `requirements*.txt`, [requirements.lock](requirements.lock) | pinned package versions |
| [manifest/](manifest/) | the test data series, attribution, geometry report |
| `results/<run>/` | results |

Test data: see [manifest/ATTRIBUTION.md](manifest/ATTRIBUTION.md) for the source collections and licenses (CC BY).
