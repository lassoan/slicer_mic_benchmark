# Method

What the benchmark measures and how. Every parameter here is also in [bench/config.py](bench/config.py) and the
section modules (`bench/t1_io.py` … `bench/t6_onnx.py`), and the code is authoritative. How to run it:
[RUNNING.md](RUNNING.md).

## Environments

On an ARM64 computer, the same Python version, CPython 3.12.10, runs in up to three builds:

| Environment | Interpreter | Extension modules (wheels) | What runs emulated |
| --- | --- | --- | --- |
| `x64` | python.org CPython amd64 (NuGet package `python`) | `win_amd64` | everything (Prism emulation) |
| `arm64ec` | ARM64EC CPython, a local build ([how to build](#building-the-arm64ec-python); optional) | `win_amd64`, the same files as `x64` | extension modules only; the interpreter is native |
| `arm64` | python.org CPython arm64 (NuGet package `pythonarm64`) | `win_arm64`, built from source where PyPI has none | nothing |

- **Comparisons:**
  - `x64` and `arm64ec` use the same wheel files, so any difference between them comes from the interpreter
    alone.
  - Comparing `arm64ec` with `arm64` shows how much emulated extension modules cost.
- **Intel/AMD computers** run `x64` only, natively, and the report shows absolute times.
- **ARM64EC:** the ARM64EC interpreter reports itself as `win-amd64`, so pip installs the x64 wheels.

### Building the ARM64EC Python

There is no official ARM64EC build of CPython. The `arm64ec` environment uses CPython 3.12.10 built with
[python-cmake-buildsystem](https://github.com/python-cmake-buildsystem/python-cmake-buildsystem), which supports
ARM64EC for Python 3.12 (CMake option `-A ARM64EC`).

- **Requirements:** a Windows ARM64 computer, Visual Studio with the MSVC ARM64EC build tools (an individual
  component in the Visual Studio Installer), CMake and git. The interpreter in the published results was built
  with Visual Studio 2026 (MSVC 19.51).
- **Libraries linked into Python must be ARM64EC or x64:**
  - libffi (needed by `ctypes`): use an x64 build, because libffi has no ARM64EC support.
  - OpenSSL (needed by `ssl` and `hashlib`, so by pip): OpenSSL has no ARM64EC target, but its x64 target
    without assembly code builds as ARM64EC. In an "ARM64" Visual Studio command prompt:

    ```bat
    set CL=/arm64EC
    perl Configure VC-WIN64A no-asm no-uplink "ARFLAGS=/nologo /MACHINE:ARM64EC"
    nmake
    nmake install
    ```

  - zlib, bzip2, xz and sqlite: build them with CMake and `-A ARM64EC`, or use x64 builds.
- **Build and install Python:**

  ```bat
  git clone https://github.com/python-cmake-buildsystem/python-cmake-buildsystem
  mkdir python-build
  cd python-build
  cmake -G "Visual Studio 18 2026" -A ARM64EC -DPYTHON_VERSION=3.12.10 ^
    -DCMAKE_INSTALL_PREFIX:PATH=<install dir> ^
    -DOPENSSL_ROOT_DIR=<OpenSSL install> -DZLIB_ROOT=<zlib install> ^
    -DLibFFI_LIBRARY=<x64 libffi .lib> -DLibFFI_INCLUDE_DIR=<libffi include> ^
    ../python-cmake-buildsystem
  cmake --build . --config Release -- /m
  cmake --build . --config Release --target INSTALL
  ```

  The project's README lists the other options, for example for bzip2, xz and sqlite.
- **Use it:** pass `<install dir>/bin/python.exe` with `--arm64ec-python`
  ([RUNNING.md](RUNNING.md#arm64-computers-the-optional-arm64ec-environment)).
- **Check it:** `sysconfig.get_platform()` must return `win-amd64`. The benchmark records the architecture of
  `python.exe` and `python312.dll` in every result (`python_exe_arch`, `python_dll_arch`), which must be `arm64ec`.
- **zlib affects the gzip results.** The interpreter in the published results links zlib-ng 1.3.1 (`zlib.ZLIB_VERSION`
  is `1.3.1.zlib-ng`). At level 1, it compresses faster but makes larger files than the zlib of the python.org
  builds, which shows in the gzip tasks of section 1 and in the zlib extra check. Link the standard zlib to avoid
  this difference.

## Rules for comparable results

- **The same package versions in every environment,** from [requirements.lock](requirements.lock).
  - If a `win_arm64` wheel is missing at the pinned version, that version is built from source
    (`scripts/build-arm64-wheels/`), not replaced by another version.
  - Unavoidable differences are listed under [Package differences](#package-differences) and in the caveats of
    each run's `findings.md`.
- **Fixed parameters and inputs.** Random data uses a fixed seed (42).
- **Outputs are checked, not just timings.** Every task returns a small result signature: a checksum, voxel count,
  point count or Dice. `scripts/compare.py` compares it with `x64`:
  - task signatures: relative tolerance
  - rendered images: mean absolute pixel difference
  - AI segmentations: Dice per label

  A fast run that computes something different does not count.
- **Timing:**
  - Each section runs in a new process, timed with `time.perf_counter()`.
  - Each task has one warm-up run, which also fills the Prism translation cache. The reported time is the median
    of 3 timed runs (`DEFAULT_REPEATS` per section).
  - AI tasks run once per case, without a warm-up; the cases are the samples.
- **Threads:** sections 2–4 run twice, with 1 thread and with all logical CPUs. The thread count is set in every
  library:
  - environment variables `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS`
  - SimpleITK: global default number of threads
  - VTK: `vtkSMPTools` (the STDThread backend when threads > 1) and `vtkMultiThreader`
  - PyTorch: `torch.set_num_threads`

  I/O, AI and ONNX run with all threads only. TotalSegmentator always uses all cores on the CPU.
- **Machine state:**
  - The computer is on AC power, in a fixed power mode.
  - The environments run interleaved, section by section, instead of one environment after another.
  - Before each run, the driver waits 60 s, then for 30 s of idle CPU (ignoring the benchmark itself).
  - `scripts/loadmon.py` logs CPU load from other processes. Runs that overlapped it (mean above 4% or peak above
    20%) are repeated once.
  - The load numbers are stored in each result as `foreign_load`.
- **Recorded with every result:**
  - Python `sys.version`, platform and machine, package versions
  - the PE machine type of every loaded extension module and DLL, which shows what actually ran emulated
  - the OpenGL renderer, for rendering
  - a computer description from `bench/sysinfo.py`: OS build, CPU core types and instruction set extensions, RAM,
    GPU and NPU with drivers, system disk, power source and mode
- **Privacy:** results are scrubbed of paths, user names and computer names when saved
  ([RUNNING.md](RUNNING.md#privacy)).

## Test data

The test data is 20 abdominal CT series from the NCI Imaging Data Commons (IDC), listed in
[manifest/idc_series.csv](manifest/idc_series.csv) (2.2 GB).

- **Selection:**
  - selected with `idc-index`: CT, abdominal, license CC BY, axial, 512×512, 100–700 slices, at most 2 series per
    patient
  - selected deterministically, sorted by `SeriesInstanceUID` after filtering
  - checked visually on a middle slice of every series
- **Sources:** 10 series from `pancreas_ct`, and 2 each from `c4kc_kits`, `tcga_kirc`, `tcga_lihc`, `cptac_pda`
  and `hcc_tace_seg`. Attribution: [manifest/ATTRIBUTION.md](manifest/ATTRIBUTION.md).
- **Geometry problems:** the geometry check flags two series:
  - case19 has 103 duplicated slice positions: two interleaved reconstructions in one series.
  - case20 has non-uniform slice spacing.

  Neither is in the compute or AI subsets.
- **Subsets:**
  - Sections 2–4 use 5 cases of different sizes and sources: `COMPUTE_CASES` = case01, case06, case11, case14,
    case18.
  - Sections 5–6 use the AI subset (`ai_subset` column of the manifest): case01, case02, case03, case11, case13.
- **Preparation:** `bench/prepare.py` converts the DICOM series to NRRD and NIfTI once. This is not timed.

## Startup

`bench/startup.py` times new processes that run the following commands:

- `python -c pass`
- the imports of numpy and scipy, SimpleITK, VTK, and torch, each on its own
- the whole stack: numpy, scipy, SimpleITK, nibabel, pynrrd, pydicom and VTK

The first run after the environment was idle is reported separately, because it may include Prism translation.
The time is the median of 5 further runs.

## Section 1: File I/O and DICOM geometry (`t1_io.py`)

All 20 series; time for the whole set. Runs with all threads.

| Task | Details | Output check |
| --- | --- | --- |
| 1a Read DICOM headers | SimpleITK `ImageFileReader.ReadImageInformation()` for every file (series UID, position, orientation, spacing, slice thickness); also pydicom (pure Python) | number of files and series |
| 1b Check geometry (pure Python) | Group by series. Per series: the normal from Image Orientation (Patient); the same orientation in all slices (tolerance 1e-4); positions projected onto the normal, sorted, with uniform spacing (max deviation < 1% of the median); missing and duplicate slices; gantry tilt. Repeated 50 times per measurement, because one pass takes about 20 ms | per-series pass/fail and spacing |
| 1c Read DICOM volumes | `sitk.ImageSeriesReader` (GDCM) with the sorted file list, converted to numpy | voxel sum, shape, spacing |
| 1d Write NRRD | pynrrd, raw and gzip level 1, with space directions and origin | file size |
| 1e Write NIfTI | nibabel, `.nii` and `.nii.gz` (level 1), affine converted from LPS to RAS | file size |
| 1f Read NRRD and NIfTI | pynrrd; nibabel `dataobj` and `get_fdata(dtype=float32)` | voxel sum equal to 1c |

## Section 2: numpy and scipy (`t2_numpy.py`)

The 5 compute cases (int16, HU), plus a synthetic 512³ float32 volume.

| Task | Details |
| --- | --- |
| 2a Element-wise operations | window/level to uint8 (W 400, L 40); z-score normalization and clip; element-wise operations on the synthetic volume |
| 2b Reductions | `np.histogram` (256 bins, −1024 to 3072); percentiles 1, 50, 99; `np.unique` |
| 2c scipy.ndimage filters | `gaussian_filter` (σ = 2 voxels); `median_filter` (3³) on a centered 256³ crop; binary dilation and erosion (3 iterations) of the body mask |
| 2d Labeling and distance | body mask (HU > −300) → `label` → largest component → `distance_transform_edt` with spacing, on the 256³ crop |
| 2e Resampling | `zoom` to 1.5 mm isotropic (order 1); `affine_transform` with a 10° rotation |
| 2f Linear algebra | PCA (SVD) of bone voxel coordinates (HU > 250); `svd` and matrix product of 2000×2000; rigid and affine landmark fit with `lstsq` (10,000 points); `eigh` of 1,000,000 3×3 matrices |
| 2g FFT | `scipy.fft.rfftn` phase correlation of the 256³ crop and a copy shifted by (5, −3, 7); the recovered shift is the check |

## Section 3: C++ algorithms (`t3_cpp.py`)

The 5 compute cases, read from the NRRD files.

| Task | Details | Output check |
| --- | --- | --- |
| 3a Anisotropic diffusion | SimpleITK curvature and gradient anisotropic diffusion, float32, 5 iterations, conductance 1.0, on a centered 192³ crop | mean and standard deviation |
| 3b Label map | bone threshold (HU > 250) → `ConnectedComponent` → `RelabelComponent` (minimum 1000 voxels) | number of components |
| 3c Label statistics | `LabelStatisticsImageFilter` and `LabelShapeStatisticsImageFilter` | volume and mean HU per label |
| 3d Histogram | VTK `vtkImageAccumulate` (4096 bins); SimpleITK image statistics | bin counts sum to the voxel count |
| 3e Surface extraction | `vtkFlyingEdges3D` → `vtkWindowedSincPolyDataFilter` (20 iterations, pass band 0.01) → `vtkPolyDataNormals` | points, triangles, area |
| 3f Surface → label map | `vtkPolyDataToImageStencil` on the original geometry → `vtkImageStencilToImage` | Dice against 3b |

## Section 4: VTK rendering (`t4_render.py`)

Offscreen, 1920×1080, on case01 and the largest compute case (case18).

| Task | Details | Metric |
| --- | --- | --- |
| 4a Surface rendering | bone surface from 3e, and a decimated copy with 25% of the triangles; the camera rotates 360° in 1° steps | first frame; 360 frames |
| 4b GPU volume ray casting | `vtkGPUVolumeRayCastMapper`, CT bone transfer function; 60 frames, because the GPU limits the frame rate in every environment | first frame (includes texture upload); 60 frames |
| 4c CPU volume ray casting | `vtkFixedPointVolumeRayCastMapper`, same settings, 36 frames (10° steps) | 36 frames |
| Image check | frames saved to PNG and compared with x64 | mean absolute difference |

Every environment renders through the same driver. On the Snapdragon test computer, this is Microsoft's
OpenGL-on-D3D12 (Mesa) on the Adreno GPU, which runs natively in every process, including inside the x64
process.

## Section 5: AI segmentation with PyTorch, CPU (`t5_ai.py`)

The 5 AI cases, all threads, one run per case.

| Task | Details | Output check |
| --- | --- | --- |
| 5a TotalSegmentator, fast | task `total`, `--fast` (3 mm), multi-label output | Dice per label against x64 |
| 5b TotalSegmentator, full resolution | task `total` (1.5 mm), on the first case only (`TOTALSEG_FULLRES_CASES`) | same |
| 5c MONAIAuto3DSeg | "Abdominal organs TS2 - quick" (3 mm, `abdominal-organs-3mm-v2.0.0`), run with the inference script of the SlicerMONAIAuto3DSeg extension, outside Slicer | same |

TotalSegmentator is installed without dipy, fury, pyarrow, blosc, imgkit and xvfbwrapper in every environment.
They have no `win_arm64` wheels and are used only for reports, previews and statistics.

## Section 6: ONNX Runtime and the NPU (`t6_onnx.py`)

The MONAIAuto3DSeg network from 5c is exported to ONNX once (`scripts/export_onnx.py`, opset 17), and every
environment uses the same file. Preprocessing and the MONAI sliding-window inferer are the same as in 5c. Only
the network evaluation differs.

| Task | Details |
| --- | --- |
| 6a Single patch | one 112×112×144 patch, median of 5 after a warm-up, with 1 thread and with all threads; PyTorch and ONNX Runtime (CPU) |
| 6b Sliding window | each AI case, all threads; PyTorch and ONNX Runtime (CPU) |
| NPU (arm64, Snapdragon only) | 6a and 6b with the `onnxruntime-qnn` plugin: Hexagon HTP backend, fp16, no CPU fallback. Uses a fixed-shape copy of the model (`scripts/make_static_onnx.py`) compiled once into an "EP context" model (`scripts/npu_probe.py --make-context`, about 17 minutes) |

Output check: Dice of the ONNX Runtime and NPU label maps against PyTorch, in each run.

## Extra checks (`bench/extra_checks.py`)

Targeted checks of results that looked suspicious. They run in each environment:

- **SVD thread scaling:** `numpy.linalg.svd` of 2000×2000 with 1, 2, 4, … and all logical CPUs. Each thread
  count runs in a new process, with the thread variables set before numpy is imported. The time is the median of
  5 after a warm-up.
- **zlib:** compression of 64 MB of CT voxels at level 1, and decompression, with the zlib version.

## Package differences

These are the only intended differences between environments. Each run's `findings.md` repeats the ones that
apply to it.

- **SimpleITK 2.5.5** (not the newest 2.5.x), because it is the newest version with a source distribution to
  build `win_arm64` from. The arm64 wheel is built with ITK 5.4.7; the official 2.5.5 wheels use 5.4.5, so the
  two differ by bug-fix releases only.
- **VTK 9.7.2 for arm64** is built from the release tag with VTK's wheel CI configuration and the default module
  set (version `9.7.2.dev0`). Its DLLs are added with `repack_vtk_wheel.py`, because delvewheel fails on ARM64.
- **PyTorch 2.15.0+cpu** from the PyTorch index everywhere, but the builds differ:
  - The `win_arm64` build has no oneDNN and uses generic CPU code.
  - The x64 build uses MKL and oneDNN with AVX2.
- **torchvision** is 0.29.1 for x64, and `0.29.1a0+cpu` for arm64 (the only 0.29.1 build for that platform). It
  is only needed for an import in nnU-Net.
