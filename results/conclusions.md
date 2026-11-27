# Main conclusions

The main results across all computers. The evidence, exact numbers and caveats are in each run's `findings.md`:

- [Snapdragon X Elite laptop](win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261123_970/findings.md)
  (ARM64, 2026-11-23)
- [Core i7-12700H laptop with RTX 3080 Ti](win_x64_cpu_i7-12700h_14x2.30GHz_ram_32GB_gpu_rtx-3080-ti-laptop+iris-xe_20261124_563/findings.md)
  (x64, 2026-11-24)
- [Core i7-8700 desktop with RTX 3060](win_x64_cpu_i7-8700_6x3.19GHz_ram_32GB_gpu_rtx-3060+uhd-630_20261124_564/findings.md)
  (x64, 2026-11-24)

Every run is listed in [README.md](README.md).

## Python on Windows ARM64

Measured on the Snapdragon X Elite.

- **Native arm64 is 1.2–1.45× faster than x64 emulation for everything except PyTorch.**
- **ARM64EC gives practically no speed-up.** Nearly all the time is spent in x64 extension modules, which are
  still emulated.
- **PyTorch on arm64 is 3–7× slower than emulated x64.** The `win_arm64` PyTorch build has no oneDNN.
- **ONNX Runtime is the fix:**
  - On the arm64 CPU, it is faster than any x64 option.
  - On the Hexagon NPU, it is a further 3.2–4.1× faster.
- **TotalSegmentator full resolution on the Snapdragon NPU takes 2.1 minutes per case.** This compares with
  51 minutes with PyTorch on native arm64, 7.8 minutes under x64 emulation, and 5.7 minutes on the Core i7-12700H
  CPU. The output matches PyTorch: mean Dice 0.9999. The cost is a one-time compile of about 3 hours.

## AI segmentation on the CPU

- **On x64 code, PyTorch is faster than ONNX Runtime for the MONAI network.**
  - Core i7-12700H: ONNX Runtime is 1.33–1.45× slower per case.
  - Core i7-8700: about the same speed, 0.95–1.05× of the PyTorch time per case.
  - Snapdragon, x64 under emulation: ONNX Runtime is also slower than PyTorch.
- **On native arm64, it is the other way round:** ONNX Runtime is 7–8× faster than PyTorch.

## AI segmentation on a GPU or NPU

- **An accelerator makes TotalSegmentator at full resolution practical.** On case01, one cold run each:

  | Computer and device | Time |
  | --- | ---: |
  | Core i7-12700H, NVIDIA RTX 3080 Ti Laptop GPU (CUDA) | 90.0 s |
  | Core i7-8700, NVIDIA RTX 3060 (CUDA) | 110.5 s |
  | Snapdragon X Elite, Hexagon NPU | 126.4 s |
  | Core i7-12700H, CPU | 340.9 s |
  | Snapdragon X Elite, x64 under emulation, CPU | 468.2 s |
  | Core i7-8700, CPU | 488.1 s |

  - Each GPU is 3.8–4.4× faster than the CPU of the same computer:
    - RTX 3080 Ti: 3.8×
    - RTX 3060: 4.4×
  - The GPU outputs match the CPU: mean Dice 0.9999.
  - The GPU needs no preparation. The NPU needs a one-time compile of about 3 hours.

## Threads

- **The C++ libraries (ITK, VTK) use the threads well.** Section 3 is 4.3× faster with 20 threads than with 1
  on the Core i7-12700H, and 3.5× faster with 12 threads on the Core i7-8700.
- **Most numpy/scipy code runs on one thread.** Section 2 takes the same time with 1 thread as with all threads
  on both x64 computers. Only the BLAS tasks (matrix multiply, SVD) gain.
- **BLAS stops scaling early.** A 2000×2000 SVD:
  - Snapdragon (arm64 OpenBLAS): no faster beyond 4 threads.
  - Core i7-12700H: fastest with 4–8 threads, slower again with 20.
  - Core i7-8700: fastest with 4 threads (2.365 s). With 12 threads it is slower than with 1 (4.16 s against
    3.782 s).
  - Don't use all hardware threads for BLAS.

## File I/O

- **gzip dominates the time of writing compressed files.** On the Core i7-12700H: 36.0 s for a gzip NRRD,
  against 2.6 s raw.
  - On the Core i7-8700, even raw writing is slow: 17.3 s for a raw NRRD and 50.0 s gzip. This is probably
    because of its older SATA SSD.
- **pydicom reads DICOM headers faster than SimpleITK:** 3.5× on the Core i7-12700H, 4.2× on the Core i7-8700.
