"""Export the 5 TotalSegmentator "total" full-resolution nnU-Net networks (Dataset291-295, 3d_fullres, fold 0) to
fixed-shape ONNX (batch 1, one 128x128x128 patch), for task 6c (bench/totalseg_npu.py). Models that exist are kept.

The network is built by nnU-Net itself (nnUNetPredictor.initialize_from_trained_model_folder, as TotalSegmentator
does), so the exported graph is the one TotalSegmentator runs. Run in the arm64 environment (nnunetv2) with the
onnx package added on PYTHONPATH (requirements-export-arm64.txt, installed to .envs/onnx-addon-arm64 by
benchmark.py data, so that the measured environment does not change).

Usage: python scripts/export_totalseg_onnx.py [--check]
  --check  compare ONNX Runtime (CPU) with torch on one random patch per model
"""

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from bench.t5_ai import TOTALSEG_HOME, setup_totalseg_env  # noqa: E402
from bench.totalseg_npu import TASK_IDS, TS_ONNX_DIR, onnx_file  # noqa: E402

WEIGHTS = TOTALSEG_HOME / "nnunet" / "results"


def model_folder(task_id):
    ds = next(WEIGHTS.glob(f"Dataset{task_id}_*"))
    return next(ds.glob("*__3d_fullres"))


def load_predictor(task_id):
    setup_totalseg_env()
    import totalsegmentator.nnunet  # noqa: F401  (registers TotalSegmentator's trainer-class lookup)
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
    pred = nnUNetPredictor(tile_step_size=0.5, use_gaussian=True, use_mirroring=False,
                           perform_everything_on_device=False, device=torch.device("cpu"), allow_tqdm=False)
    pred.initialize_from_trained_model_folder(str(model_folder(task_id)), use_folds=[0],
                                              checkpoint_name="checkpoint_final.pth")
    net = pred.network
    net.load_state_dict(pred.list_of_parameters[0])
    net.eval()
    return pred, net


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    torch.set_num_threads(os.cpu_count())
    TS_ONNX_DIR.mkdir(parents=True, exist_ok=True)
    for tid in TASK_IDS:
        if onnx_file(tid).exists():
            continue
        pred, net = load_predictor(tid)
        patch = list(pred.configuration_manager.patch_size)
        x = torch.from_numpy(np.random.default_rng(0).standard_normal((1, 1, *patch), dtype=np.float32))
        out = onnx_file(tid)
        t0 = time.perf_counter()
        torch.onnx.export(net, (x,), str(out), input_names=["input"], output_names=["output"],
                          opset_version=17, dynamo=False)
        print(f"Dataset{tid}: patch {patch}, {len(pred.dataset_json['labels'])} labels, exported {out.name} "
              f"({out.stat().st_size / 1e6:.1f} MB) in {time.perf_counter() - t0:.1f} s")
        if args.check:
            import onnxruntime as ort
            sess = ort.InferenceSession(str(out), providers=["CPUExecutionProvider"])
            with torch.no_grad():
                ref = net(x).numpy()
            y = sess.run(None, {"input": x.numpy()})[0]
            print(f"  output {y.shape}, max abs diff vs torch {np.abs(y - ref).max():.2e}, "
                  f"argmax agreement {(y.argmax(1) == ref.argmax(1)).mean():.6f}")


if __name__ == "__main__":
    main()
