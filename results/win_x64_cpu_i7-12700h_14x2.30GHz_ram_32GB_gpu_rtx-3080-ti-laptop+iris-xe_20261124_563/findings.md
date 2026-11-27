# Findings: Core i7-12700H laptop with RTX 3080 Ti (2026-11-24)

Intel Core i7-12700H (14 cores: 6 performance + 8 efficiency, 20 threads), 32 GB, NVIDIA RTX 3080 Ti Laptop GPU
and Intel Iris Xe, Windows 11 build 26200, on AC power. Single pass, no replicate. Only the x64 environment
applies on this computer.

## Summary

**Output:** x64 is the reference environment, so there is nothing to compare against on this computer. All task
checks passed, and no run failed.

Total time per section (sum of the task medians, in seconds):

| Section | 1 thread | 20 threads |
| --- | ---: | ---: |
| Python startup and imports | 4.3 | |
| 1. File I/O and DICOM geometry (20 CTs) | | 130.0 |
| 2. numpy/scipy | 80.7 | 79.6 |
| 3. C++ (SimpleITK, VTK) | 127.1 | 29.3 |
| 4. VTK rendering | 56.1 | 14.7 |
| 5. AI segmentation with PyTorch (CPU) | | 549.3 |
| 6. MONAI network, PyTorch and ONNX Runtime (CPU) | | 253.5 |

## Conclusions

- **The C++ libraries use the threads well. numpy/scipy code mostly doesn't.**
  - Section 3 is 4.3× faster with 20 threads than with 1 thread.
    - `3d_image_statistics_sitk`: 1.079 s → 0.111 s (9.7×)
    - `3e_flying_edges`: 0.677 s → 0.113 s (6.0×)
    - `3f_polydata_to_labelmap_stencil`: 58.9 s → 10.0 s (5.9×)
    - `3a_curvature_anisotropic_diffusion`: 28.3 s → 6.186 s (4.6×)
    - No gain: `3d_histogram_vtkImageAccumulate` (0.900 s / 0.898 s)
  - Section 2 has the same total with 1 and 20 threads (80.7 s and 79.6 s).
    - Only the BLAS tasks gain: `2f_matmul_2000` 0.140 s → 0.037 s (3.8×), `2f_svd_2000` 2.343 s → 1.871 s.
    - The scipy filters, interpolation and labelling run on one thread.
- **More BLAS threads make the SVD slower after 4–8 threads.**
  - 2000×2000 SVD: 2.376 s with 1 thread, 1.395 s with 4, 1.403 s with 8, 1.551 s with 16 and 1.888 s with 20.
  - Probably because the work is spread over the slower efficiency cores and hyper-threads.
- **Rendering on the GPU is fast and doesn't depend on the CPU threads.**
  - Surface rendering, 360 frames at 1920×1080: 0.35–0.64 s.
  - GPU volume rendering, 60 frames: 0.69–1.49 s.
  - CPU volume rendering, 36 frames: 50.3 s with 1 thread, 8.987 s with 20 threads (5.6×).
- **gzip dominates the file I/O time.**
  - Writing NRRD: 2.641 s raw, 36.0 s gzip. Writing NIfTI: 1.953 s raw, 31.5 s gzip.
  - Reading NRRD: 1.468 s raw, 12.9 s gzip.
  - zlib 1.3.1 compresses 64 MB in 0.868 s (ratio 0.512).
  - pydicom reads the DICOM headers 3.5× faster than SimpleITK (2.203 s against 7.738 s).
- **PyTorch on the CPU is faster than ONNX Runtime for the MONAI network.**
  - Sliding-window inference, per case: PyTorch 12.1–28.8 s, ONNX Runtime 17.4–39.2 s. ONNX Runtime is
    1.33–1.45× slower.
  - One patch, 20 threads: PyTorch 2.924 s, ONNX Runtime 4.040 s. With 1 thread: 10.3 s and 11.5 s.
  - Sections 5 and 6 run on the CPU. Only task 5d uses the GPU (see below).
- **TotalSegmentator on the CPU:**
  - fast mode: 17.7–36.9 s per case
  - full resolution, case01: 340.9 s (5.7 minutes)
  - MONAIAuto3DSeg abdominal organs: 6.234–24.1 s per case
- **TotalSegmentator full resolution on the RTX 3080 Ti is 3.8× faster than on the CPU** (task 5d, run later, on
  2026-11-27).
  - case01: 90.0 s on the GPU, against 340.9 s on the CPU (5b).
  - This is one cold run. It includes loading the models and starting CUDA.
  - The output matches the CPU: mean Dice 0.9999 over 52 labels, lowest 0.9977.
  - PyTorch 2.15.0+cu132, CUDA 13.2, cuDNN 9.26, 16 GB GPU memory.

## Caveats

- **One machine and one pass.** Each value is the median of 3 timed repeats after a warm-up. The AI tasks
  (sections 5 and 6) have one run per case.
- **Load from other processes:**
  - The driver repeated the 20-thread file I/O run because of outside load. The repeat also overlapped load:
    6.8% of the machine on average and 27.6% at most. Treat the section 1 times as slightly pessimistic.
  - In every other section, outside load was 1.4–3.0% on average and 12.1% at most.
  - During task 5d (2026-11-27), outside load was 10.2% on average and 16.5% at most. AI runs are not repeated.
    The effect is probably small, because the task runs on the GPU.
- **Hybrid CPU.** "20 threads" mixes performance cores, efficiency cores and hyper-threads. So the scaling is not
  comparable with a CPU that has only one kind of core.
- **Computer id fixed after the run.** The system scan listed USB input devices as NPUs, because the WMI filter
  `Name LIKE '%NPU%'` also matches "Input". The filter is fixed in `bench/sysinfo.py`. The misdetected devices
  were removed from this run's files, and the run was renamed accordingly. This computer has no NPU.
