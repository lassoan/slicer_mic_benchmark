"""All benchmark parameters in one place."""

import csv
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DICOM_DIR = DATA / "dicom"
NRRD_DIR = DATA / "nrrd"        # prepared once (bench/prepare.py), input for sections 2-5
NIFTI_DIR = DATA / "nifti"      # prepared once, input for section 5
WORK_DIR = DATA / "work"        # per-environment scratch output
RESULTS_DIR = ROOT / os.environ.get("BENCH_RESULTS", "results")
MANIFEST = ROOT / "manifest" / "idc_series.csv"


def manifest():
    with MANIFEST.open() as f:
        return list(csv.DictReader(f))


def all_cases():
    return [r["case_id"] for r in manifest()]


def ai_cases():
    return [r["case_id"] for r in manifest() if r["ai_subset"] == "1"]


# Sections 2-4 use a fixed subset of cases with different sizes and sources to keep the run time manageable.
COMPUTE_CASES = ["case01", "case06", "case11", "case14", "case18"]

# --- Section 1: I/O and geometry
GEOMETRY_ORIENTATION_TOL = 1e-4      # max difference of direction cosines between slices
GEOMETRY_SPACING_REL_TOL = 0.01      # max deviation of slice spacing from the median, relative
NRRD_GZIP_LEVEL = 1
NIFTI_GZIP_LEVEL = 1

# --- Section 2: numpy/scipy
WINDOW, LEVEL = 400.0, 40.0
HIST_BINS, HIST_RANGE = 256, (-1024, 3072)
GAUSSIAN_SIGMA = 2.0
MEDIAN_SIZE = 3
CROP = 256                           # centered cube used for median filter, distance transform and FFT
MORPH_ITERATIONS = 3
BODY_THRESHOLD = -300
BONE_THRESHOLD = 250
RESAMPLE_SPACING = 1.5
ROTATION_DEG = 10.0
FFT_SHIFT = (5, -3, 7)
SYNTH_SIZE = 512
SYNTH_SEED = 42
SVD_SIZE = 2000
LSTSQ_POINTS = 10000
EIGH_BATCH = 1_000_000

# --- Section 3: C++ algorithms
DIFFUSION_ITERATIONS = 5
DIFFUSION_CROP = 192               # diffusion runs on the centered 192^3 region (full volumes take minutes)
DIFFUSION_CONDUCTANCE = 1.0
MIN_COMPONENT_SIZE = 1000
ACCUMULATE_BINS = 4096
SMOOTH_ITERATIONS = 20
SMOOTH_PASSBAND = 0.01

# --- Section 4: rendering
RENDER_SIZE = (1920, 1080)
RENDER_CASE = "case01"
RENDER_CASE_LARGE = "case18"
SURFACE_FRAMES = 360
VOLUME_GPU_FRAMES = 60
VOLUME_CPU_FRAMES = 36
DECIMATE_KEEP = 0.25

# --- Section 5: AI
TOTALSEG_FULLRES_CASES = 1
