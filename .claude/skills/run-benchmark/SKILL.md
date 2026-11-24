---
name: run-benchmark
description: Run the medical image computing benchmark on this computer, check the results, write results/<run>/findings.md with the conclusions, and prepare the run for publishing. Use when asked to run, rerun or finish the benchmark, analyze a run, or add a computer's results.
---

# Run the benchmark and add findings

You are running a timing benchmark. Your own activity can distort the timings, so keep the computer quiet while
it runs. [RUNNING.md](../../../RUNNING.md) is the full manual. Read it if something here is unclear.

## 1. Check prerequisites

- **OS:** Windows 10/11, x64 or ARM64. Check `$env:PROCESSOR_ARCHITECTURE` or `python bench/sysinfo.py`.
- **Disk:** at least 15 GB free on the drive of the repository.
- **Starter Python:** any Python 3.9+ to start the driver. On Windows, `python` may be the Microsoft Store alias,
  which does nothing. Try `py -3`. After `setup`, use `.envs/nuget-python/tools/python.exe`.
- **ARM64 only:**
  - `wheels/arm64/` must hold the locally built wheels (SimpleITK, VTK, cc3d, ndindex). If it is missing, ask
    the user to copy it or to agree to the 3-hour build ("ARM64 computers" in RUNNING.md). Without the wheels,
    the arm64 environment is skipped.
  - The `arm64ec` environment needs an ARM64EC CPython. Ask the user for the path; it is passed with
    `--arm64ec-python`. If there is none, continue without it.
- **The user:** tell them that a full run takes 4–8 hours, needs AC power and sleep turned off, and that they
  should not use the computer meanwhile. Get their go-ahead.

## 2. Set up and download data

```
python benchmark.py setup [--arm64ec-python <path>]
python benchmark.py data
```

These steps don't measure anything, so other work is fine meanwhile. They are restartable: repeat a step after a
network error. Fix setup errors (for example a missing wheel) before running. A failed environment is reported and
then skipped.

## 3. Run

Start the run detached, so that it survives the end of your session, and send its console output to a file in
the results folder. In PowerShell:

```
Start-Process -WindowStyle Hidden -FilePath .envs\nuget-python\tools\python.exe `
  -ArgumentList "benchmark.py run [--arm64ec-python <path>]" `
  -RedirectStandardOutput results\run.console.log -RedirectStandardError results\run.console.err.log -PassThru
```

`*.log` files in `results/` are not committed, because they contain local paths.

The run creates `results/<computer id>_<YYYYMMDD>_<000-999>/`. The progress log is
`results/<run>/run-<date>-<time>.log`, with one `=== HH:MM:SS <env> <section> threads=N` line per run.

While it runs:

- **Don't add CPU load.** No builds, test suites, package installs or large file operations.
- **Check progress rarely.** Every 30 minutes or more, with cheap commands only: `tail` of the run log, `grep`
  for `FAILED`, and whether the process is alive.
- The driver records load from other processes in `load.log`, and repeats runs that overlapped it.
- **Expected:** a `FAILED` line is a real problem. Note it and look at the console log, but don't stop the run.
- **Finished:** the run log ends with `benchmark finished`. After that, the driver writes the summary, the report
  and `results/all.csv`, then runs the privacy check.

## 4. Verify

All checks are on the new `results/<run>/` folder:

1. Read the end of the run log and the console logs:
   - Count the `FAILED` runs.
   - Note the runs that "still overlapped load from other processes".
2. Read `summary.md`:
   - **Output checks:** rendered images match x64, segmentation Dice is about 1.0, and task checks agree. A
     mismatch is a finding. Report it; don't hide it.
   - **Missing environments or sections:** explain why each is missing (no wheels, no ARM64EC Python, no NPU).
3. Run `python scripts/check_privacy.py results/<run>`. It must print no hits.
   - Results must never contain the user name, computer name or absolute paths.
   - If anything is found, fix the cause in `bench/privacy.py`, then run `scripts/scrub_results.py` on the
     folder. Don't edit the JSON by hand.
4. If an earlier run of the same computer exists, compare the two runs:
   `python scripts/compare_reps.py results/<run> results/<earlier run>`.

## 5. Write `results/<run>/findings.md`

This file is the human summary of the run. It is published in the repository and included in the report and
on the website. Base every number on `summary.md`, `summary.json`, `extra_checks.json` and `replicates.md`. Don't
invent numbers, and don't round them more than the data supports.

Use this structure. See
`results/win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261123_970/findings.md`
for an example.

```markdown
# Findings: <short computer description> (<date>)

<CPU (cores), RAM, Windows build, power source>. <Which run this is; replicates, if any.>

## Summary

**Output:** <did every environment produce the same output as x64; exceptions>

<Table: speed-up vs x64 per section (geometric mean), one column per non-x64 environment. On an x64-only
computer: total time per section instead.>

## Conclusions

- **<one bold sentence per main result>**, with the evidence as nested bullets (task names, times, ratios)

## Caveats

- <number of repeats, outside load, reruns, package build differences, anything unusual>
```

Rules:

- **Content:** state what was measured, not speculation. Mark explanations as such ("probably because …").
- **Privacy:** no personal information. Don't mention the user, the computer name, local paths or names of
  other running programs. Describe outside load only as numbers.
- **Style:** short sentences and nested bullets, not long paragraphs.

## 6. Regenerate and hand over

```
.envs\nuget-python\tools\python.exe benchmark.py report --results results/<run>
```

This puts `findings.md` into the report as notes, updates `results/all.csv` and `results/README.md`, and runs
the privacy check again. Open `reports/<run>/report.html` and check that the findings show up.

Tell the user:

- the main results
- any failures or caveats
- the report path

To publish, the files to commit are `results/<run>/` (logs and images are ignored by `.gitignore`),
`results/all.csv` and `results/README.md`. Commit, push or open a pull request only when the user asks. Pushing
to the main branch rebuilds the results website.
