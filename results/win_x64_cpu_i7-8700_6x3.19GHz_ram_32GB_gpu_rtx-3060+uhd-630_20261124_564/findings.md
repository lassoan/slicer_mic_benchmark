# Findings: Intel Core i7-8700 desktop with RTX 3060 (2026-11-24)

Intel Core i7-8700 (6 cores, 12 threads), 32 GB, NVIDIA GeForce RTX 3060, Windows 11 build 26200, desktop
(mains power).

Single run, x64 only. There is no earlier run of this computer to use as a replicate. Every section except
startup was run twice, because other processes used the CPU during the first pass. The tables use the second pass.

## Summary

**Output:** only the x64 environment applies to this computer, so there is nothing to compare across environments.

- All task checks passed, and no run failed.
- ONNX Runtime and PyTorch segmentations of the same network agree: mean Dice over labels is 0.99955–0.99999
  per case.

Total time per section (sum of the task medians):

| Section | 1 thread | 12 threads |
| --- | ---: | ---: |
| Python startup and imports | 7.0 s | |
| 1. File I/O and DICOM geometry (20 CTs) | | 236.6 s |
| 2. numpy/scipy | 108.1 s | 106.4 s |
| 3. C++ (SimpleITK, VTK) | 196.3 s | 56.2 s |
| 4. VTK rendering (RTX 3060) | 82.7 s | 22.9 s |
| 5. AI segmentation with PyTorch (CPU) | | 783.0 s |
| 6. MONAI network, PyTorch and ONNX Runtime (CPU) | | 324.4 s |

## Conclusions

- **The SimpleITK and VTK filters scale with threads; numpy/scipy code doesn't.**
  - C++ section: 3.5× faster with 12 threads (196.3 s → 56.2 s).
    - curvature anisotropic diffusion: 52.3 s → 14.0 s
    - surface → label map stencil: 76.3 s → 20.6 s
  - CPU volume rendering: 75.6 s → 16.0 s (4.7×).
  - numpy/scipy section: 108.1 s → 106.4 s. The scipy filters and element-wise operations run on one thread.
  - Only BLAS tasks gain: `matmul_2000` 0.160 s → 0.067 s, `svd_2000` 3.731 s → 2.585 s.
- **SVD is slowest with all 12 threads.** In the extra check, a 2000×2000 SVD takes:
  - 1 thread: 3.782 s
  - 4 threads: 2.365 s (fastest)
  - 8 threads: 2.39 s
  - 12 threads: 4.16 s
  - Probably because 12 threads include the 6 hyper-threads.
- **Writing files is slow even without compression.**
  - Writing NRRD: 17.3 s raw, 50.0 s gzip. Writing NIfTI: 36.0 s raw, 43.3 s gzip.
  - Raw NRRD writing took 35.9 s in the first pass.
  - Reading is fast without compression: NRRD 1.835 s raw, 13.3 s gzip.
  - Probably because of the older SATA SSD. zlib alone compresses 64 MB in 1.093 s (ratio 0.512).
  - pydicom reads the DICOM headers 4.2× faster than SimpleITK (4.792 s against 19.9 s).
- **GPU rendering is interactive.** On the RTX 3060, 360 frames of the full-resolution surface take 0.52–0.89 s.
  60 frames of GPU volume rendering take 0.78–1.86 s.
- **AI segmentation on the CPU:**
  - TotalSegmentator fast: 24.5–43.6 s per case.
  - TotalSegmentator full resolution: 488.1 s (8.1 minutes) for case01.
  - MONAIAuto3DSeg abdominal organs: 9.1–37.1 s per case.
- **TotalSegmentator full resolution on the RTX 3060 GPU takes 110.5 s, 4.4× faster than on the CPU (488.1 s).**
  This is task 5d, added on 2026-11-27.
  - PyTorch 2.15.0+cu132, CUDA 13.2, 12 GB GPU memory.
  - One cold run for case01, including loading the models and starting CUDA.
  - The output matches the CPU result: mean Dice 0.9999 over 52 labels, lowest label 0.9977.
  - Load from other processes during the run: 12.3% of the machine on average, 18.0% at most.
- **ONNX Runtime is not faster than PyTorch here.** Same MONAIAuto3DSeg network, 12 threads (ONNX Runtime
  time / PyTorch time: 0.95–1.05 per case):
  - one patch: PyTorch 4.086 s, ONNX Runtime 4.714 s
  - sliding window, per case: PyTorch 18.6–42.7 s, ONNX Runtime 19.4–44.1 s
  - Only on case11 is ONNX Runtime faster (19.5 s against 20.5 s).
  - ONNX Runtime 1.32 had only CPU execution providers; no NPU was used.
- **Compared with the Snapdragon X Elite run** (`…_snapdragon-x1e80100_…_20261123_970`):
  - The Snapdragon's native arm64 environment is faster for:
    - startup: its section times are 0.50× this computer's (geometric mean of the tasks)
    - I/O: 0.39×
    - numpy/scipy: 0.71–0.76×
    - C++: 0.55–0.67×
  - It is slower for:
    - rendering: 1.13–1.16×, probably because of the RTX 3060 here
    - PyTorch AI: 3.26×
  - ONNX Runtime sliding window on case01 takes 11.0 s on Snapdragon arm64, against 19.7 s here.
  - PyTorch sliding window on case01 takes 15.9 s on the Snapdragon (x64 under emulation), against 18.7 s here.

## Caveats

- **One machine and one run.** Each value is the median of 3 timed repeats after a warm-up. The AI tasks have one run
  per case.
- **Load from other processes:** this computer was never idle.
  - Before starting the run, the driver waited for load from other processes to be below 6% of the machine for
    30 s. With that limit, the startup section ran after a 2-hour wait. No other section started in the next
    2 hours.
  - The rest of the run used a limit of 10% (`--idle-load 10`).
  - Mean load from other processes during the sections was 7.9–16.3% of the machine, with peaks of 13.0–40.0%.
    Every section is listed as "still overlapped load", including the repeats.
  - The highest load was during C++ with 12 threads (mean 16.3%, max 40.0%). Multithreaded times are likely
    slowed the most.
- **Repeat agreement:** for each section, the median ratio of task times between the two passes is 0.98–1.04.
  - Exceptions:
    - `1d_write_nrrd_raw`: 35.9 s → 17.3 s
    - `2f_matmul_2000` (12 threads): 0.052 s → 0.067 s
    - `2f_svd_2000` (12 threads): 3.152 s → 2.585 s
    - `2b_histogram` (1 thread): 3.928 s → 3.253 s
    - `3e_windowed_sinc_smoothing` (12 threads): 1.926 s → 2.214 s
  - Treat differences of less than about 20% between computers with care.
- **Computer id fixed after the run.** The system scan listed USB input devices as NPUs, because the WMI filter
  `Name LIKE '%NPU%'` also matches "Input". The filter is fixed in `bench/sysinfo.py`. The misdetected devices
  were removed from this run's files, and the run was renamed accordingly. This computer has no NPU.
