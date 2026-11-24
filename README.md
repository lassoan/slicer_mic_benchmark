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

## Quick start

On a Windows 10/11 computer (x64 or ARM64) with Python 3.9+ and about 15 GB of free disk space:

```bat
git clone https://github.com/lassoan/slicer_mic_benchmark.git mic-benchmark-py
cd mic-benchmark-py
python benchmark.py all
```

This takes 4–8 hours.

- [RUNNING.md](RUNNING.md): requirements, steps and options, output files, privacy, contributing results, and
  ARM64 specifics (locally built wheels, ARM64EC, NPU).
- [.claude/skills/run-benchmark/SKILL.md](.claude/skills/run-benchmark/SKILL.md): instructions that let an AI
  coding agent run the benchmark and write the findings.

## Results

[results/](results/README.md) has every run, with a findings summary per computer, `summary.md` and
machine-readable CSV/JSON. The reports with charts are on the repository's GitHub Pages site.

First results, on a Snapdragon X Elite laptop
([findings](results/win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon_20261123_970/findings.md)):

- **Native arm64 is 1.2–1.45× faster than x64 emulation for everything except PyTorch.**
- **ARM64EC gives practically no speed-up.**
- **PyTorch on arm64 is 3–7× slower than emulated x64.**
- **ONNX Runtime is the fix:**
  - On the arm64 CPU, it is faster than any x64 option.
  - On the Hexagon NPU, it is a further 3–4× faster.

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

## Test data

Test data: see [manifest/ATTRIBUTION.md](manifest/ATTRIBUTION.md) for the source collections and licenses (CC BY).
