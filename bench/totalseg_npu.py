"""TotalSegmentator "total" full resolution with its 5 nnU-Net networks on the Snapdragon Hexagon NPU (task 6c).

Everything except the network evaluation is TotalSegmentator's and nnU-Net's own code (cropping, resampling,
preprocessing, sliding window with Gaussian weighting, export). Only nnUNetPredictor._internal_maybe_mirror_and_predict,
the call that evaluates the network on one 128x128x128 patch, is replaced (while the NpuPredictor context is active)
by an ONNX Runtime session on the NPU (QNN EP plugin, HTP backend, fp16, no CPU fallback) of the matching model.

Models: each network (Dataset291-295, 3d_fullres, fold 0) is exported to fixed-shape ONNX
(scripts/export_totalseg_onnx.py) and compiled into an "EP context" model (scripts/totalseg_npu.py compile; about
35 minutes and 5 GB of memory per model, done once by benchmark.py data).
"""

import time
from pathlib import Path

import numpy as np

from bench import config

TS_ONNX_DIR = config.DATA / "models" / "onnx" / "totalseg"
TASK_IDS = [291, 292, 293, 294, 295]


def onnx_file(tid):
    return TS_ONNX_DIR / f"Dataset{tid}_3d_fullres.onnx"


def ctx_file(tid):
    return TS_ONNX_DIR / f"Dataset{tid}_3d_fullres-qnn-htp-fp16_ctx.onnx"


def available():
    return all(ctx_file(t).exists() for t in TASK_IDS)


class NpuPredictor:
    """Context manager: while active, nnU-Net evaluates its networks on the NPU. Collects statistics in .stats."""

    def __init__(self):
        self.sessions = {}
        self.stats = {"patches": 0, "npu_s": 0.0, "load_s": 0.0}

    def __enter__(self):
        import torch
        from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
        from bench.t6_onnx import npu_session
        cls = nnUNetPredictor
        self.orig = (cls.initialize_from_trained_model_folder, cls._internal_maybe_mirror_and_predict)
        orig_init = self.orig[0]
        sessions, stats = self.sessions, self.stats

        def init(pred, model_training_output_dir, *a, **kw):
            orig_init(pred, model_training_output_dir, *a, **kw)
            tid = int(Path(model_training_output_dir).parent.name[len("Dataset"):][:3])
            if tid not in sessions:
                t0 = time.perf_counter()
                sessions[tid] = npu_session(ctx_file(tid))
                stats["load_s"] += time.perf_counter() - t0
                if sessions[tid] is None:
                    raise RuntimeError(f"no NPU session for Dataset{tid}")
            pred._npu_session = sessions[tid]

        def predict(pred, x):
            if pred.use_mirroring:
                raise RuntimeError("test-time mirroring is not supported on the NPU")
            t0 = time.perf_counter()
            y = pred._npu_session.run(None, {"input": x.numpy().astype(np.float32, copy=False)})[0]
            stats["npu_s"] += time.perf_counter() - t0
            stats["patches"] += 1
            return torch.from_numpy(y)

        cls.initialize_from_trained_model_folder = init
        cls._internal_maybe_mirror_and_predict = predict
        return self

    def __exit__(self, *exc):
        from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
        nnUNetPredictor.initialize_from_trained_model_folder, nnUNetPredictor._internal_maybe_mirror_and_predict = \
            self.orig
        self.sessions.clear()
        return False


def seg_dice(ref_path, path):
    """Mean and minimum Dice over the labels present in the reference segmentation (as in scripts/compare.py)."""
    import nibabel as nib
    a = np.asarray(nib.load(str(ref_path)).dataobj).astype(np.int32)
    b = np.asarray(nib.load(str(path)).dataobj).astype(np.int32)
    d = []
    for lb in np.unique(a):
        if lb:
            x, y = a == lb, b == lb
            d.append(2 * np.logical_and(x, y).sum() / (x.sum() + y.sum()))
    return {"mean": round(float(np.mean(d)), 4), "min": round(float(np.min(d)), 4), "labels": len(d)}
