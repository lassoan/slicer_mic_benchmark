# Running the benchmark

What each task measures, and the rules for comparable results: [METHOD.md](METHOD.md).

Requirements:

- Windows 10/11 (x64 or ARM64)
- any Python 3.9+ to start the driver (python.org or `py`)
- internet access
- about 15 GB of free disk space
- 4–8 hours

No administrator rights are needed: the driver downloads its own Python interpreters (python.org NuGet packages)
into `.envs/`.

```bat
git clone https://github.com/lassoan/slicer_mic_benchmark.git mic-benchmark-py
cd mic-benchmark-py
python benchmark.py all
```

An AI coding agent can do all of this, including checking the results and writing the findings. See
[Using an AI agent](#using-an-ai-agent).

`all` runs these steps, which can also be run one at a time:

| Command | What it does | Time |
| --- | --- | --- |
| `python benchmark.py setup` | Downloads CPython 3.12.10 (x64; ARM64 on ARM64 computers) and creates the virtual environments in `.envs/`: `tools` (helper, not timed) and one per benchmark environment, with exactly the versions in [requirements.lock](requirements.lock) | 5–15 min |
| `python benchmark.py data` | Downloads the 20 CT series listed in [manifest/idc_series.csv](manifest/idc_series.csv) from the NCI Imaging Data Commons (2.2 GB) and converts them to NRRD/NIfTI. Downloads the TotalSegmentator and MONAIAuto3DSeg models and exports the MONAI network to ONNX. On a Snapdragon computer, also compiles the NPU models | 20–60 min; on a Snapdragon computer 1.5–3 h more |
| `python benchmark.py run` | Runs all sections in all environments (interleaved), repeats runs that overlapped CPU load from other programs, runs the extra checks, then writes the report | 3–7 h |
| `python benchmark.py report` | Rewrites the summary and the report from existing results | 1–3 min |

Each step skips work that is already done, so a step can be repeated after an error.

## For reliable timings

- Close other programs and keep the computer on AC power.
- Turn off sleep for the duration of the run.
- Don't use the computer during the run. The driver waits for an idle CPU before each run, and it logs and
  repeats runs disturbed by other processes. It cannot remove the effect of thermal throttling or power-saving
  modes.

## Output

Each `run` writes to a new folder `<run>` = `<computer id>_<date>_<time of day as 000–999>` (one unit is 86.4 s),
for example `win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261124_234`.
The computer id is a compact hardware description (`python bench/sysinfo.py --short`). `report` without
`--results` uses the newest folder of this computer.

- `results/<run>/<env>/*.json`: raw results, one file per section, thread count and environment.
  - They include machine, package and loaded-DLL architecture metadata.
  - The computer description is in `environment.system`: OS, CPU cores and instruction set extensions, RAM type
    and speed, GPU, NPU, system disk, power source and mode.
  - `python bench/sysinfo.py` prints this description for any computer. `--json` gives all details. It uses only
    the standard library and also works on Linux and macOS.
- `results/<run>/summary.md`: all tasks with times and speed-ups. Also in this folder:
  - `tasks.csv`: one row per task, environment and thread count (machine-readable)
  - `summary.json`: the same as `summary.md`, plus the output checks
  - `extra_checks.json`
  - `findings.md` (optional, hand-written): conclusions and caveats, included in the report as notes
  - local only, not in source control:
    - `load.log`: CPU load and names of other programs during the run
    - `run-*.log`: console output
    - `<env>/images/`: rendered frames, compared with x64 in `summary.json`
- `results/all.csv` and `results/README.md`: every run combined (CSV) and an index of the runs. GitHub shows the
  index when you open the [results](results/) folder.
- `results/conclusions.md` (hand-written): the main conclusions across all computers, with links to each run's
  `findings.md`.
- `reports/<run>/report.html` and `report.md`: the report. It contains:
  - machine and environments
  - automatically derived key findings, and `findings.md` if present
  - time per section, speed-ups, AI backends, extra checks and every task

  The HTML file is self-contained (charts built in, light and dark mode). `reports/` is not in source control.

**Results website:** on every push that changes `results/`, a GitHub workflow
([.github/workflows/pages.yml](.github/workflows/pages.yml)) builds the reports of all runs with
`scripts/make_site.py`. It publishes them on the repository's GitHub Pages site, with `all.csv` and each run's
`tasks.csv` and `summary.json`.

## Privacy

Results are meant to be published, so they contain no personal information:

- Paths are stored relative to `<repo>`, `<python>`, `<home>`, `<windows>` and similar roots, or as file names
  only.
- No computer or user names are stored.
- The load of other programs is stored as numbers only, without process names.

[bench/privacy.py](bench/privacy.py) does this when results are saved. `scripts/check_privacy.py` checks the
results at the end of `report` and in the GitHub workflow. Results written before this existed were cleaned with
`scripts/scrub_results.py`.

## Contributing results

1. Run the benchmark.
2. Optionally, write `results/<run>/findings.md` and run `python benchmark.py report --results results/<run>`.
3. Optionally, update `results/conclusions.md` where the new run confirms, contradicts or extends a conclusion.
4. Commit the new `results/<run>/` folder together with `results/all.csv`, `results/README.md` and
   `results/conclusions.md` in a pull request.

## Options for `run`

| Option | Default | Meaning |
| --- | --- | --- |
| `--envs x64,arm64` | all environments that apply to the computer | environments to run, in this order |
| `--sections io,cpp` | all sections | subset of `startup,io,numpy,cpp,render,ai,onnx` |
| `--threads 1,all` | `1,all` | thread counts for numpy, cpp and render; io, ai and onnx always use all threads |
| `--results DIR` | a new `results/<run>` | results folder (an existing one adds to it); the report goes to `reports/<folder name>` |
| `--replicate DIR` | | results of an earlier run, compared in the report |
| `--cooldown 60` | 60 | seconds of rest before each run |
| `--idle 30` | 30 | seconds of idle CPU, ignoring the benchmark, required before each run |
| `--idle-load 6` | 6 | CPU load of other processes (% of the machine) below which the CPU counts as idle; raise it on a computer whose background load never drops below 6% |
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

Two runs of the same computer can be compared with
`python scripts/compare_reps.py results/<run A> results/<run B>`, which writes `results/<run A>/replicates.md`.

## ARM64 computers: locally built wheels

PyPI has no `win_arm64` wheels for SimpleITK 2.5.5, VTK 9.7.2, connected-components-3d 4.1.1 or ndindex 1.10.1.
`setup` installs them from `wheels/arm64/` (or `--wheels DIR`). Without them, `setup` reports the error and
continues with the other environments. There are two ways to get the wheels:

- **Copy** the folder `wheels/arm64` (65 MB) from a computer that has it. The wheels work on any Windows ARM64
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

## ARM64 computers: the optional ARM64EC environment

There is no official ARM64EC build of CPython. The `arm64ec` environment needs a CPython 3.12.10 built for
ARM64EC: see [Building the ARM64EC Python](METHOD.md#building-the-arm64ec-python). Pass it with
`--arm64ec-python <path to python.exe>` or the `ARM64EC_PYTHON` environment variable. Without one, `arm64ec` is
skipped.

## ARM64 computers: the NPU

On a Snapdragon X computer, the arm64 environment gets the `onnxruntime-qnn` plugin
([requirements-npu.txt](requirements-npu.txt)). `data` compiles the MONAI network for the Hexagon NPU once. This
takes about 17 minutes and makes a 1.9 GB file in `data/models/onnx/`. If there is no NPU, or compiling fails, the
NPU tasks are skipped.

For task 6c (TotalSegmentator full resolution on the NPU), `data` also exports the 5 TotalSegmentator networks to
ONNX and compiles each for the NPU. This takes about 35 minutes and 5 GB of memory per network; as many run in
parallel as fit in the free memory (3 with 32 GB). The models take 3.6 GB in `data/models/onnx/totalseg/`. If a
step fails, task 6c is skipped. To check the models: `.envs\arm64\Scripts\python scripts\totalseg_npu.py patch`.

## Using an AI agent

The agent skill [.claude/skills/run-benchmark/SKILL.md](.claude/skills/run-benchmark/SKILL.md) tells an AI coding
agent how to run the benchmark and add its analysis. It covers:

- setup, and running the benchmark without disturbing the timings
- checking the results for failures, outside load and private information
- writing `results/<run>/findings.md`

Claude Code picks the skill up automatically. Ask it to "run the benchmark". Other agents find it through
[AGENTS.md](AGENTS.md).
