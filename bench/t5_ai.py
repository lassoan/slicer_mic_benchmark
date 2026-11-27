"""Section 5: AI segmentation on CPU (TotalSegmentator and MONAIAuto3DSeg) on the AI subset of cases.

5a TotalSegmentator task "total", --fast (3 mm), multi-label output
5b TotalSegmentator task "total", full resolution (1.5 mm), on the first TOTALSEG_FULLRES_CASES cases
5c MONAIAuto3DSeg "Abdominal organs TS2 - quick" (3 mm), inference script of the Slicer extension
5d TotalSegmentator as 5b, on an NVIDIA GPU (PyTorch CUDA). Only when CUDA is available: benchmark.py runs it in the
   x64 environment with the CUDA build of PyTorch (requirements-cuda.txt) on PYTHONPATH, on computers with an NVIDIA
   GPU. Output check: Dice against the CPU result of 5b in the same environment.

Only run with all threads: TotalSegmentator always sets torch to use all cores on CPU.
Segmentations are saved in data/work/<env>/seg/ and compared with the x64 results in compare.py.
"""

import os
import time
from pathlib import Path

import numpy as np

from bench import config, harness

DEFAULT_REPEATS = 1

MODELS_DIR = config.DATA / "models"
TOTALSEG_HOME = MODELS_DIR / "totalseg"
MONAI_DIR = MODELS_DIR / "monai"
MONAI_RELEASES = "https://github.com/lassoan/SlicerMONAIAuto3DSeg/releases/download/Models/"
MONAI_MODELS = {
    "abdominal-organs-3mm-v2.0.0": MONAI_RELEASES + "abdominal-organs-3mm-v2.0.0.zip",
}


def setup_totalseg_env():
    TOTALSEG_HOME.mkdir(parents=True, exist_ok=True)
    os.environ["TOTALSEG_HOME_DIR"] = str(TOTALSEG_HOME)
    os.environ["TOTALSEG_WEIGHTS_PATH"] = str(TOTALSEG_HOME / "nnunet" / "results")


def label_signature(path):
    import nibabel as nib
    import nrrd
    if str(path).endswith(".nrrd"):
        data, _ = nrrd.read(str(path))
    else:
        data = np.asarray(nib.load(str(path)).dataobj)
    counts = np.bincount(data.astype(np.int64).ravel())
    labels = int((counts[1:] > 0).sum())
    return {"labels": labels, "foreground_voxels": int(counts[1:].sum())}


def run_totalseg(case, out, fast, threads, device="cpu"):
    """TotalSegmentator task "total", multi-label output; on the CPU, or "gpu" (CUDA). Also used by task 6c (NPU)."""
    from totalsegmentator.python_api import totalsegmentator
    totalsegmentator(config.NIFTI_DIR / f"{case}.nii.gz", out, ml=True, fast=fast, task="total",
                     device=device, nr_thr_resamp=threads, nr_thr_saving=min(threads, 6), quiet=True)


def cuda_info():
    """GPU and CUDA versions if PyTorch can use an NVIDIA GPU, else None."""
    import torch
    if not torch.cuda.is_available():
        return None
    p = torch.cuda.get_device_properties(0)
    return {"torch": torch.__version__, "cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
            "gpu": p.name, "gpu_memory_gb": round(p.total_memory / 2**30, 1), "gpu_count": torch.cuda.device_count()}


def run(runner, cases=None, tasks=None, threads=1, env="unknown"):
    cases = cases or config.ai_cases()
    setup_totalseg_env()
    import torch  # noqa: F401  (import before setting threads)
    harness.set_library_threads(threads)
    seg_dir = config.WORK_DIR / env / "seg"
    seg_dir.mkdir(parents=True, exist_ok=True)

    def want(name):
        return tasks is None or any(name.startswith(t) for t in tasks)

    if want("5a") or want("5b"):
        def ts(case, fast):
            def fn():
                out = seg_dir / f"{case}-totalseg-{'fast' if fast else 'full'}.nii.gz"
                run_totalseg(case, out, fast, threads)
                return label_signature(out)
            return fn

        if want("5a"):
            for case in cases:
                runner.run(f"5a_totalseg_fast_{case}", ts(case, True), warmup=0)
        if want("5b"):
            for case in cases[:config.TOTALSEG_FULLRES_CASES]:
                runner.run(f"5b_totalseg_full_{case}", ts(case, False), warmup=0)

    if want("5c"):
        from bench.third_party.auto3dseg_segresnet_inference import main as monai_main
        for name in MONAI_MODELS:
            model_file = next((MONAI_DIR / name).rglob("model.pt"))
            for case in cases:
                def fn(case=case):
                    out = seg_dir / f"{case}-monai-{name}.nrrd"
                    monai_main(model_file=str(model_file), image_file=str(config.NRRD_DIR / f"{case}.nrrd"),
                               result_file=str(out))
                    return label_signature(out)
                runner.run(f"5c_monai_{name}_{case}", fn, warmup=0)

    extra = {"cases": cases}
    if want("5d"):
        info = cuda_info()
        if info is None:
            if tasks:  # asked for explicitly (benchmark.py does this on computers with an NVIDIA GPU)
                print("5d skipped: PyTorch has no CUDA GPU here (CPU build of PyTorch, no NVIDIA GPU, or the "
                      "driver is too old for this CUDA version)")
        else:
            import torch
            from bench.totalseg_npu import seg_dice
            info["dice_vs_cpu"] = {}
            for case in cases[:config.TOTALSEG_FULLRES_CASES]:
                out = seg_dir / f"{case}-totalseg-full-cuda.nii.gz"

                def fn(case=case, out=out):
                    run_totalseg(case, out, False, threads, device="gpu")
                    torch.cuda.synchronize()
                    return label_signature(out)
                runner.run(f"5d_totalseg_full_cuda_{case}", fn, warmup=0)
                ref = seg_dir / f"{case}-totalseg-full.nii.gz"
                if ref.exists():
                    info["dice_vs_cpu"][case] = seg_dice(ref, out)
                print(f"  {case}: TotalSegmentator full resolution on {info['gpu']}: Dice vs CPU "
                      f"{info['dice_vs_cpu'].get(case)}")
            extra["cuda"] = info
    return extra
