# Medical image computing benchmark on Windows ARM64: plan

Measure how fast typical medical image computing workloads run in Python on a Windows ARM64 (Snapdragon)
machine with three builds of the same Python version:

| Environment | Interpreter | Extension modules (wheels) | What runs emulated |
| --- | --- | --- | --- |
| `x64` | python.org CPython 3.12.10 amd64 | `win_amd64` | Everything (Prism emulation) |
| `arm64ec` | ARM64EC CPython 3.12.10 (local build with python-cmake-buildsystem) | `win_amd64` (same wheel set as `x64`) | Extension modules only; the interpreter is native |
| `arm64` | python.org CPython 3.12.10 arm64 | `win_arm64` (built from source where none is published) | Nothing |

`x64` and `arm64ec` use the same wheel files, so any difference between them comes from the interpreter alone.
Comparing `arm64ec` with `arm64` shows how much emulated extension modules cost.

Optional, for the in-application view: run the same tasks in `Slicer --python-script` with the installed x64
Slicer 5.12.4 (emulated) and a native ARM64 Slicer build.

## Status (2026-11-23)

Phases 0 and 1 and all six sections are implemented. Everything (setup, data, run, report) is driven by
`benchmark.py` (see README.md), which writes `results/<run>/summary.md` via `scripts/compare.py` and the report
via `scripts/make_report.py`.

Differences from the original plan, and why:

- **Base interpreters:** x64 and arm64 CPython 3.12.10 come from the python.org NuGet packages (`python`,
  `pythonarm64`), extracted to `.envs/`, so no installer runs. ARM64EC is a local CPython build (`--arm64ec-python`).
- **SimpleITK 2.5.5 instead of 2.5.8:** PyPI has no 2.5.8 source distribution to build a `win_arm64` wheel from.
  The arm64 wheel is the one built by the ARM64 Slicer build (same recipe as
  `scripts/build-arm64-wheels/build_simpleitk.sh`). It uses ITK 5.4.7, while the official 2.5.5 wheels use ITK 5.4.5
  (bug-fix releases only).
- **VTK 9.7.2 for arm64 built from source** with VTK's own wheel CI configuration, limited to the default module
  set (`scripts/build-arm64-wheels/build_vtk.bat`). DLLs were added with `repack_vtk_wheel.py` because
  delvewheel fails on ARM64 (API-set DLLs). Both builds use the Sequential SMP backend by default; the harness
  switches to STDThread when threads > 1.
- **PyTorch 2.15.0+cpu** from the PyTorch index in all environments. The `win_arm64` build has no oneDNN
  (`USE_MKLDNN=OFF`, CPU capability `DEFAULT`), while the x64 build uses MKL and oneDNN with AVX2. torchvision 0.29.1
  (`0.29.1a0+cpu` for arm64, the only 0.29.1 build for that platform), only needed for an import in nnU-Net.
- **TotalSegmentator installed without** dipy, fury, pyarrow, blosc, imgkit and xvfbwrapper (no `win_arm64`
  wheels; used only for reports, previews and statistics). The same reduced set is used in all environments.
- **Compute subset:** sections 2 and 3 use 5 cases (`COMPUTE_CASES`). Median filter, distance transform and FFT use
  a centered 256³ crop, and anisotropic diffusion a 192³ crop, because the full volumes take minutes per task.
- **Rendering:** GPU volume rendering uses 60 frames instead of 360, because it is GPU-bound (same frame rate in all
  environments). Every environment renders through the same OpenGL driver: Microsoft's OpenGL-on-D3D12 (Mesa
  26.3) on the Adreno X1-85, native in every process (ARM64EC inside the x64 process).
- **AI:** all threads only (TotalSegmentator always sets torch to use every core on CPU). Full-resolution
  TotalSegmentator on 1 case; MONAIAuto3DSeg with "Abdominal organs TS2 - quick" (3 mm) on the 5 AI cases.
  One run per case (no warm-up); the 5 cases are the samples.
- **Section 1** also parses all headers with pydicom (pure Python), and the geometry check is repeated 50 times per
  measurement (one pass takes about 20 ms). I/O runs with all threads only.
- **Test data:** 10 series from `pancreas_ct`, 2 each from `c4kc_kits`, `tcga_kirc`, `tcga_lihc`, `cptac_pda`
  and `hcc_tace_seg` (2.2 GB). The geometry check flags two of them: case19 has 103 duplicated slice positions
  (two interleaved reconstructions in one series), and case20 has non-uniform slice spacing. Neither is in the
  compute or AI subsets.

### Additions after the first run (2026-11-24)

- **Outside-load protection:** another session's builds overlapped parts of the first pass. `scripts/loadmon.py`
  now logs CPU load from other processes and waits for an idle machine before each run. Runs that overlapped load
  were repeated (now done automatically by `benchmark.py run`).
- **Second full pass:** the main result, in `results/<computer id>_20261123_970`, run in the reverse environment order.
  The first pass in `results/<computer id>_20261123_754` is kept as a replicate, and `scripts/compare_reps.py` compares the two.
- **Section 6, ONNX Runtime 1.32 and the NPU (`bench/t6_onnx.py`):**
  - The MONAIAuto3DSeg network is exported to ONNX (`scripts/export_onnx.py`).
  - For the NPU: a copy with fixed shapes, made with `onnxruntime.tools.make_dynamic_shape_fixed` and onnx
    shape inference.
  - The NPU runs with the `onnxruntime-qnn` 2.8.0 plugin (HTP, fp16), installed in the arm64 environment only.
    `scripts/npu_probe.py --make-context` compiles the "EP context" model once.
- **Targeted checks (`bench/extra_checks.py`):** SVD thread scaling, and zlib vs zlib-ng.

## Rules for comparable results

- **The same package versions in every environment** (one `requirements.lock` file). If a `win_arm64` wheel is not
  available at the pinned version, build that version from source and keep the wheel in `wheels/arm64/`. Do not
  silently use a different version; record any unavoidable difference in `results/NOTES.md`.
- **Fixed parameters and inputs.** Every task's parameters are written in this plan and in `bench/config.py`.
  Random data uses a fixed seed.
- **Check outputs as well as timings.** Every task returns a small result signature (checksum, voxel count, point count,
  Dice) that must match the `x64` reference within a tolerance. A fast run that computes something different does
  not count.
- **Timing:** one warm-up run (also fills the Prism translation cache), then the median of 5 runs (AI tasks: median of 3).
  Use `time.perf_counter()` inside the process; each section runs in a new process.
- **Threads:** run sections 2–5 twice, once with 1 thread and once with all cores. Set the thread count everywhere:
  `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`,
  `sitk.ProcessObject.SetGlobalDefaultNumberOfThreads()`, `vtkSMPTools.Initialize()`,
  `vtkMultiThreader.SetGlobalMaximumNumberOfThreads()`, `torch.set_num_threads()`.
- **Machine state:** on AC power, the same power mode, no other heavy processes, and a 60 s idle period before each
  section to limit thermal effects. Run the environments interleaved (x64, arm64ec, arm64, repeat) instead of
  one after the other.
- **Record the environment** with every result: CPU, Windows build, Python `sys.version`, `sysconfig.get_platform()`,
  `platform.machine()`, package versions, and the **PE machine type of every loaded extension module and DLL**
  (read with `pefile`). This shows what actually ran emulated. Also record `GL_RENDERER` and `GL_VERSION` for
  rendering. `bench/sysinfo.py` adds a full computer description (model, OS build, CPU core types and instruction
  set extensions, RAM type and speed, GPU and NPU with drivers, system disk, power source and power mode, measured
  at the end of each run); the report flags runs with a different power state.
- Also measure **startup and import time** separately: a cold run (after a reboot) and a warm run of
  `python -c "import numpy, scipy, SimpleITK, vtk, nibabel, nrrd"`.

## Repository layout

```
mic-benchmark-py/
  PLAN.md
  README.md                  how to set up environments and run
  requirements.lock          pinned versions shared by all environments
  envs/setup-x64.ps1         create venvs, install wheels
  envs/setup-arm64ec.ps1
  wheels/arm64/              locally built win_arm64 wheels
  data/                      (git-ignored) dicom/, nrrd/, nifti/, seg/
  manifest/idc_series.csv    selected series with UIDs, collection, license, size
  bench/
    harness.py               timing, threads, env metadata, JSON output
    config.py                all task parameters
    t1_io.py  t2_numpy.py  t3_cpp.py  t4_render.py  t5_ai.py
  scripts/
    download_idc.py          select and download test data
    compare.py               results/<run>/*.json -> summary.md
    make_report.py           summary -> reports/<run>/report.md, report.html
  benchmark.py               driver: setup, data, run (interleaved, load guard, reruns), report
  results/<run>/<env>/<date>-<section>-t<threads>.json
```

## Phase 0: Environments

- [x] Install python.org 3.12.10 amd64 and arm64 (per-user, side by side) and create one venv for each.
- [x] Create an `arm64ec` venv from the ARM64EC CPython build. It reports itself as `win-amd64`,
      so pip installs the x64 wheels.
- [x] Install `requirements.lock` in all three: numpy, scipy, SimpleITK, pynrrd, nibabel, pydicom, vtk,
      torch (CPU), TotalSegmentator, monai, idc-index, pefile.
- [x] `arm64`: list which packages have no `win_arm64` wheel at the pinned version (expected candidates: vtk,
      some TotalSegmentator/nnU-Net dependencies). Build them from source, or use locally built wheels. If VTK cannot be built in time, run sections 3 and 4 for `arm64` in the native ARM64
      Slicer Python instead and note that.
- [x] Write a smoke test that imports everything and prints the PE machine type of each loaded module.

## Phase 1: Test data (20 abdominal CT series from IDC)

- [x] Select with `idc-index` (SQL on the IDC index): `Modality = 'CT'`, abdominal body part (`BodyPartExamined`
      in `ABDOMEN`, `ABDOMENPELVIS`, `CHEST_ABDOMEN_PELVIS`, or abdominal collections), license CC BY,
      axial series with 100–700 slices and 512×512 matrix.
- [x] Use mixed sources so the geometry checks see real-world variation: about 10 series from a curated research
      collection (for example `pancreas_ct`) and about 10 from clinical-trial or TCGA/CPTAC collections
      (for example `tcga_kirc`, `tcga_lihc`, `cptac_pda`), with at most 2 series per patient.
- [x] Select deterministically (sorted by `SeriesInstanceUID` after filtering) and save the selection to
      `manifest/idc_series.csv` with collection, patient, study and series UIDs, slice count, size and license, so
      the same data can be downloaded again.
- [x] Download with `idc-index` / `s5cmd` into `data/dicom/<SeriesInstanceUID>/`. Expect about 3–6 GB. Downloading is
      setup work and is not timed.
- [x] Keep the attribution text the licenses require in `manifest/ATTRIBUTION.md`.

## Section 1: File I/O and DICOM geometry (`t1_io.py`)

Every task runs over all 20 series. The time for the whole set is reported, and the time per series is kept in the JSON.

| Task | Details | Output check |
| --- | --- | --- |
| 1a Read DICOM headers | `sitk.ImageFileReader` + `ReadImageInformation()` for every file; collect `0020\|000e`, `0020\|0032`, `0020\|0037`, `0028\|0030`, `0018\|0050` | Number of files and series |
| 1b Check geometry (pure Python) | Group by Series Instance UID; per series: compute the normal from Image Orientation (Patient); check that all slices have the same orientation (tolerance 1e-4); project Image Position (Patient) onto the normal, sort, and check that the spacing is uniform (max deviation < 1% of the median spacing) and that there are no missing slices or duplicates; report gantry tilt / shear | Per-series pass/fail and spacing; must be identical in all environments |
| 1c Read DICOM volumes | `sitk.ImageSeriesReader` (GDCM) with the sorted file list from 1b; convert to a numpy array | Voxel sum, shape, spacing |
| 1d Write NRRD | `pynrrd`: once raw and once gzip-compressed (level 1), with space directions and origin | File size |
| 1e Write NIfTI | `nibabel`: `.nii` and `.nii.gz`, affine converted from LPS to RAS | File size |
| 1f Read NRRD and NIfTI | `pynrrd` and `nibabel` (`get_fdata(dtype=float32)` and the raw `dataobj`) | Voxel sum and geometry equal to 1c |

Kept as an output: the volumes in `data/nrrd/` and `data/nifti/` are the inputs for the later sections.
Windows file caching affects I/O times, so report both the first run and the warm runs.

## Section 2: Vectorized Python algorithms (`t2_numpy.py`)

Inputs: the 20 CT volumes (int16, in HU), plus one synthetic 512³ float32 volume (seed 42) for fixed-size timing.

| Task | Details |
| --- | --- |
| 2a Element-wise operations | Window/level to uint8 (W 400, L 40), z-score normalization, clip, type conversions |
| 2b Reductions | Histogram (`np.histogram`, 256 bins from −1024 to 3071), percentiles (1, 50, 99), `np.unique` on the label map |
| 2c scipy.ndimage filters | `gaussian_filter` (σ = 2 voxels), `median_filter` (3³) on a 256³ crop, `binary_dilation`/`binary_erosion` (3 iterations) of the body mask |
| 2d Distance and labeling | Body mask (HU > −300) → `label` → keep the largest component → `distance_transform_edt` (with spacing) |
| 2e Resampling | `scipy.ndimage.zoom` to 1.5 mm isotropic (order 1) and `affine_transform` with a 10° rotation |
| 2f Linear algebra | PCA (SVD) of the coordinates of the bone voxels (HU > 300); `np.linalg.svd` of 2000×2000; `lstsq` landmark fit (rigid + affine, 10k points); `eigh` of 3×3 structure tensors (batch of 1M) |
| 2g FFT | `scipy.fft.rfftn` of 256³; phase correlation between a volume and a shifted copy of it (the recovered shift is the output check) |

## Section 3: C++ algorithms (`t3_cpp.py`)

All on the 20 CT volumes (from the NRRD files written in section 1).

| Task | Details | Output check |
| --- | --- | --- |
| 3a Anisotropic diffusion | SimpleITK `CurvatureAnisotropicDiffusion` on float32, 5 iterations, time step 0.0625 (scaled by spacing), conductance 1.0; also `GradientAnisotropicDiffusion` with the same settings | Mean and standard deviation of the output |
| 3b Label map | Bone = threshold HU > 250 → `ConnectedComponent` → `RelabelComponent` (minimum size 1000 voxels) | Number of components |
| 3c Label statistics | SimpleITK `LabelStatisticsImageFilter` (CT as intensity, with histogram) and `LabelShapeStatisticsImageFilter` (volume, centroid, oriented bounding box, Feret diameter off) | Volume and mean HU per label |
| 3d Histogram | VTK `vtkImageAccumulate` (4096 bins) and SimpleITK `MinimumMaximum` + histogram via `LabelStatistics` | Bin counts sum to the number of voxels |
| 3e Surface extraction | `vtkFlyingEdges3D` on the bone label (value 0.5 on a 0/1 image) → `vtkWindowedSincPolyDataFilter` (20 iterations, pass band 0.01, `NormalizeCoordinatesOn`, `BoundarySmoothingOff`, `FeatureEdgeSmoothingOff`) → `vtkPolyDataNormals` | Number of points and triangles, surface area (`vtkMassProperties`) |
| 3f Surface → label map | `vtkPolyDataToImageStencil` on the original image geometry → `vtkImageStencilToImage` | Dice against the 3b label > 0.95 |

## Section 4: C++ visualization (`t4_render.py`)

Offscreen render window (1920×1080, `SetOffScreenRendering(1)`), on one fixed case and on the largest case.

| Task | Details | Metric |
| --- | --- | --- |
| 4a Surface rendering | Bone surface from 3e (and a decimated version with 25% of the triangles) with `vtkPolyDataMapper`; the camera rotates 360° in 1° steps | Time to first frame; median frame time over 360 frames |
| 4b GPU volume ray casting | `vtkGPUVolumeRayCastMapper` with a CT bone preset transfer function, sample distance 0.5 × spacing, same camera path | Time to first frame (includes texture upload); median frame time |
| 4c CPU volume ray casting | `vtkFixedPointVolumeRayCastMapper` with the same settings; 36 frames (10° steps) | Median frame time (this is the CPU emulation case) |
| 4d Image check | Save frames 0 and 90 to PNG and compare them with the `x64` reference (`vtkImageDifference`) | Error below a threshold |

Record the OpenGL driver (`GL_RENDERER`, `GL_VERSION`) for each environment. An emulated x64 process may get a
different OpenGL implementation (for example the Microsoft OpenCL and OpenGL Compatibility Pack instead of the
native driver), and that would change the rendering results more than CPU emulation does.

## Section 5: AI segmentation (`t5_ai.py`)

CPU only (no CUDA on this machine). CPU inference is slow, so this section uses a fixed subset of 5 series
(listed in `manifest/idc_series.csv`).

| Task | Details | Output check |
| --- | --- | --- |
| 5a TotalSegmentator, fast | `TotalSegmentator -i <nifti> -o <out> --fast --device cpu --ml --task total` (3 mm model) | Dice per organ against the `x64` output > 0.98 |
| 5b TotalSegmentator, full resolution | Same without `--fast`, on 2 of the 5 series | Same |
| 5c MONAIAuto3DSeg | Inference script of the SlicerMONAIAuto3DSeg extension (`auto3dseg_segresnet_inference.py`), run outside Slicer, with a pinned CT abdominal organ model from its model list | Same |

- Download the model weights once into a shared folder (`TOTALSEG_HOME_DIR`, MONAIAuto3DSeg model cache) before
  timing starts.
- Report preprocessing, inference and postprocessing time separately when the tool logs them, plus the total time
  and peak memory (`psutil`).
- Expected outcome: `arm64ec` gains little here, because PyTorch (x64 oneDNN/AVX kernels) is still emulated;
  `arm64` uses native ARM64 PyTorch kernels.

## Reporting (`compare.py`)

- `results/summary.md`: one table per section with rows = tasks, columns = environments; time in seconds and
  speed-up relative to `x64` (higher is better); single-thread and all-thread results next to each other.
- Summary line per section: geometric mean of the speed-ups.
- List any failed output checks; their timings are not used.
- Optional: an HTML page with bar charts of speed-up per task.

## Milestones

1. Phase 0 + Phase 1: environments created, smoke test passes, 20 series downloaded, manifest saved.
2. Harness + section 1 + section 2 run in all three environments (pure Python and numpy cover most of the
   interpreter question).
3. Sections 3 and 4 (needs VTK in all environments).
4. Section 5 (needs PyTorch and TotalSegmentator in all environments).
5. Final run of everything interleaved, `summary.md` written, conclusions added to `README.md`.

## Risks and open questions

- **ARM64 wheels:** VTK, PyTorch and some nnU-Net dependencies may have no `win_arm64` wheel at the pinned
  version. Building them can take a long time; the fallback is the native ARM64 Slicer Python for VTK.
- **Version differences:** if the `arm64` environment needs a different version of a package, its speed may differ
  for reasons unrelated to the architecture. Record it and, if possible, also time that version on `x64`.
- **AVX emulation:** x64 wheels pick SIMD kernels at runtime based on the CPU features that Prism reports. Record
  which code path numpy and OpenBLAS select (`np.show_runtime()`), since it affects the emulated results a lot.
- **Thermal throttling** on a laptop during long runs: interleave environments and check whether repeated runs
  slow down.
- **Smart App Control** must stay off, or locally built binaries (ARM64EC Python, ARM64 wheels) are blocked.
- **IDC data selection:** body part tags are often missing or wrong; check the selection by looking at a middle
  slice of every series before freezing the manifest.

### Portability (2026-11-24)

- `benchmark.py` replaces the shell scripts: it downloads the python.org NuGet interpreters, creates the
  environments, downloads data and models (the IDC series from the committed manifest), exports the ONNX model and
  the fixed-shape copy (`scripts/make_static_onnx.py`, byte-identical to the model used here), compiles the NPU
  model on Snapdragon computers, runs everything, repeats runs disturbed by other processes, and writes the report.
- Environments are chosen from the processor architecture: Intel/AMD computers run x64 only (the report then shows
  absolute times); ARM64 computers run x64, arm64 and, if an ARM64EC Python is given, arm64ec.
- SVD thread-scaling counts follow the number of logical CPUs. Report findings are derived from the data.

