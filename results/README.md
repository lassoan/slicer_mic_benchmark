# Benchmark results

One folder per benchmark run: `<computer id>_<date>_<time of day as 000-999>`. How to run the benchmark and add a run: [RUNNING.md](../RUNNING.md).

Main conclusions across all computers: [conclusions.md](conclusions.md).

Human-readable, per run:

- `<run>/findings.md`: conclusions and caveats, written by whoever ran the benchmark (if present)
- `<run>/summary.md`: every task with times and speed-ups
- the report with charts: the repository's results website

Machine-readable:

- [all.csv](all.csv): every task of every run, one row per task, environment and thread count (columns: run, computer_id, cpu, os, timestamp, env, python_arch, section, threads, task, median_s, min_s, max_s, first_s, repeats, foreign_load_mean, foreign_load_max)
- `<run>/tasks.csv`: the same for one run; `<run>/<env>/*.json`: raw results with full metadata; `<run>/summary.json`: per-task times and speed-ups, output checks

Speed-up = geometric mean over the non-AI tasks of time in x64 / time in the environment (x64 is emulated on ARM64 computers).

| Date | Computer | Environments | Speed-up vs x64 | Run |
| --- | --- | --- | --- | --- |
| 2026-11-24 | GIGABYTE AORUS 17 YE5, Windows 11 Education 25H2 x64, 12th Gen Intel(R) Core(TM) i7-12700H (14C/20T), 32.0 GB RAM, NVIDIA GeForce RTX 3080 Ti Laptop GPU, Intel(R) Iris(R) Xe Graphics | x64 | – | [findings](win_x64_cpu_i7-12700h_14x2.30GHz_ram_32GB_gpu_rtx-3080-ti-laptop+iris-xe_20261124_563/findings.md), [summary](win_x64_cpu_i7-12700h_14x2.30GHz_ram_32GB_gpu_rtx-3080-ti-laptop+iris-xe_20261124_563/summary.md), [csv](win_x64_cpu_i7-12700h_14x2.30GHz_ram_32GB_gpu_rtx-3080-ti-laptop+iris-xe_20261124_563/tasks.csv) |
| 2026-11-23 | Snapdragon(R) X 12-core X1E80100 @ 3.40 GHz, 12 logical CPUs, 31.6 GB RAM, Windows 10.0.26300 | x64, arm64ec, arm64 | arm64ec 1.04×, arm64 1.34× | [findings](win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261123_970/findings.md), [summary](win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261123_970/summary.md), [csv](win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261123_970/tasks.csv) |
| 2026-11-23 | Snapdragon(R) X 12-core X1E80100 @ 3.40 GHz, 12 logical CPUs, 31.6 GB RAM, Windows 10.0.26300 | x64, arm64ec, arm64 | arm64ec 1.02×, arm64 1.32× | [summary](win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261123_754/summary.md), [csv](win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261123_754/tasks.csv) |
