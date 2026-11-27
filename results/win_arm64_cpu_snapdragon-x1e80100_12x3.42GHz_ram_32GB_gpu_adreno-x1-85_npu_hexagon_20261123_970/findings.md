# Findings: Snapdragon X Elite laptop (2026-11-23/24)

Snapdragon X Elite X1E80100 (12 cores), 32 GB, Windows 11 build 26300, on AC power.

This folder holds the main result: a full pass that logged CPU load from other processes and repeated the runs that
overlapped it. The earlier pass `…_20261123_754` is used as a replicate. The two passes are compared in
`replicates.md`.

## Summary

**Output:** in every section, every environment produced the same output as x64:

- task checks passed
- rendered images were byte-identical
- segmentation Dice ≥ 0.9999

There is one exception, in section 6: in one case (case13), the ONNX Runtime segmentation on arm64 has 0.4%
fewer foreground voxels than on x64.

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

¹ Mostly from the gzip tasks (2.7–2.9×). This is not an architecture effect. The ARM64EC Python links
zlib-ng, which at level 1 compresses 2.8× faster but makes 38% larger files: data is compressed to 71% of its
original size instead of 51%. Without the gzip tasks, ARM64EC is close to 1.0×.

## Conclusions

- **Native arm64 is 1.2–1.45× faster than x64 emulation for everything except PyTorch.**
  - Largest gains:
    - pure Python: up to 1.8×
    - anisotropic diffusion: 1.7–2.2×
    - surface → label map stencil: 1.7×
    - FFT, `np.unique`, least-squares fit: about 2.2×
    - histograms and binary morphology: about 1.75×
  - About the same speed in every environment, so nothing is gained on arm64:
    - GPU volume rendering, which goes through the same native OpenGL-on-D3D12 driver in every process
    - memory-bound scipy filters (Gaussian, median, distance transform)
- **ARM64EC gives practically no speed-up.**
  - The interpreter is native, but nearly all the time is spent in x64 extension modules (numpy, SimpleITK,
    VTK, PyTorch), which are still emulated.
  - It speeds up only pure-Python code (1.34× on the geometry check).
  - Its value is compatibility, not speed.
- **PyTorch on native arm64 is 3–7× slower than emulated x64 PyTorch.**
  - The `win_arm64` PyTorch 2.15 build has no oneDNN and uses only generic CPU code. The x64 build's MKL/oneDNN
    AVX2 kernels stay fast under emulation.
  - TotalSegmentator fast: about 100 s per case on arm64, against 31 s on x64.
  - TotalSegmentator full resolution: 51 minutes on arm64, against 7.8 minutes on x64.
- **For AI, use ONNX Runtime, and the NPU where there is one.** Times for the same MONAIAuto3DSeg network,
  sliding-window inference, per case:

  | Backend | case01 | case02 | case03 | case11 | case13 |
  | --- | ---: | ---: | ---: | ---: | ---: |
  | PyTorch, x64 (emulated), 12 threads | 15.9 s | 37.6 s | 37.7 s | 16.6 s | 17.5 s |
  | PyTorch, arm64, 12 threads | 91.9 s | 204.5 s | 203.9 s | 91.1 s | 91.7 s |
  | ONNX Runtime 1.32, x64 (emulated), 12 threads | 20.1 s | 43.1 s | 43.9 s | 20.6 s | 21.8 s |
  | ONNX Runtime 1.32, arm64, 12 threads | 11.0 s | 28.6 s | 28.1 s | 10.8 s | 10.9 s |
  | **ONNX Runtime + QNN on the Hexagon NPU (fp16)** | **3.2 s** | **6.9 s** | **6.9 s** | **3.4 s** | **3.1 s** |

  - **Speed:**
    - ONNX Runtime on the arm64 CPU is 7–8× faster than arm64 PyTorch. It is also 1.4–1.6× faster than the best
      x64 result (PyTorch).
    - The NPU is 3.2–4.1× faster than the fastest CPU result (ONNX Runtime on arm64). It is 4.9–5.6× faster
      than x64 PyTorch and 27–30× faster than arm64 PyTorch.
  - **Agreement with the PyTorch label maps** (mean Dice over labels, per case):
    - ONNX Runtime: 0.9996–0.9997, except case13 at 0.9945
    - NPU: 0.9986–0.9998
  - **NPU setup:**
    - The whole network runs on the NPU, with no CPU fallback.
    - Compiling takes about 17 minutes and is done once. The result is saved as a 1.9 GB "EP context" model
      that loads in 6 s.
    - The model needs fixed input shapes.
- **TotalSegmentator full resolution on the NPU: 2.1 minutes instead of 51** (task 6c, case01, added on
  2026-11-27).
  - This is the same TotalSegmentator call as task 5b, but its 5 nnU-Net networks run on the NPU (fp16, no CPU
    fallback). Cropping, resampling, preprocessing, the sliding window and writing the result stay on the CPU.
  - Speed:
    - 24× faster than PyTorch on arm64 (50.6 min)
    - 3.7× faster than PyTorch under x64 emulation (7.8 min)
    - 3.8× faster than ARM64EC (8.0 min)
  - Where the 126 s go:
    - NPU: 90 patches of 128³ voxels at 0.48 s each, 44 s in total
    - loading the 5 compiled models: 12.5 s
    - CPU work: the remaining 70 s, now more than half of the run
  - Agreement with the PyTorch result (task 5b): mean Dice over the 52 labels 0.9999, minimum 0.9979, against
    both arm64 and x64.
  - NPU setup:
    - Each network is compiled once: about 35 minutes and 5 GB of memory, about 3 hours for all 5 one after the
      other. The compiled models take 3 GB.
    - The NPU runs one patch at a time. Sending patches from several threads or sessions is not faster.
- **Other observations:**
  - **Linear algebra threading on arm64:** the arm64 OpenBLAS in the numpy/scipy wheels stops scaling at 4
    threads. A 2000×2000 SVD takes 2.96 s with 1 thread, 2.06 s with 4 threads and 2.27 s with 12 threads. x64
    reaches 1.48 s.
  - **zlib:** compression on native arm64 is 1.35× faster than on x64.

## Caveats

- **One machine.** Each value is the median of 3 timed repeats after a warm-up. The AI tasks have one run per
  case.
- **Task 6c was added later.** It ran on 2026-11-27 with the same environments, 3 days after the rest of this
  run. Its result file holds only this task (`arm64/20261127-090859-onnx-t12.json`), which `compare.py` adds to
  section 6. During it, other load averaged 4.6% of the machine, above the 4% limit that triggers a repeat. Most
  of it was the Windows `System` process, very likely the NPU driver and the loading of the 3 GB of models, which
  are part of the task. A repeat would show the same, so the run was not repeated.
- **Load from other processes:**
  - During the first pass, another build ran on the same machine and slowed some runs, mainly AI, by 20–40%.
  - The main pass waited for an idle machine before each run, logged outside load, and repeated the runs that
    overlapped it.
- **Package builds differ by platform:**
  - SimpleITK 2.5.5 is used everywhere, but the arm64 wheel is built with ITK 5.4.7 (official wheels use 5.4.5).
  - VTK 9.7.2 for arm64 is built from source.
  - torchvision is 0.29.1 for x64 and ARM64EC, and `0.29.1a0+cpu` for arm64.
