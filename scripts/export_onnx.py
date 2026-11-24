"""Export the MONAIAuto3DSeg network to ONNX (once; the same file is used by all environments).

Usage: python scripts/export_onnx.py   (tools environment with requirements-export.txt; benchmark.py data does this)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from bench.t6_onnx import ONNX_DIR, ONNX_FILE, load_torch_model  # noqa: E402


def main():
    torch.set_num_threads(1)
    net, cfg = load_torch_model()
    roi = cfg["roi_size"]
    x = torch.from_numpy(np.random.default_rng(0).random((1, 1, *roi), dtype=np.float32))
    ONNX_DIR.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(net, (x,), str(ONNX_FILE), input_names=["input"], output_names=["output"],
                      dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}}, opset_version=17, dynamo=False)
    import onnxruntime as ort
    sess = ort.InferenceSession(str(ONNX_FILE), providers=["CPUExecutionProvider"])
    with torch.no_grad():
        ref = net(x).numpy()
    out = sess.run(None, {"input": x.numpy()})[0]
    print(f"exported {ONNX_FILE} ({ONNX_FILE.stat().st_size / 1e6:.1f} MB), output {out.shape}, "
          f"max abs diff vs torch {np.abs(out - ref).max():.2e}, argmax agreement "
          f"{(out.argmax(1) == ref.argmax(1)).mean():.6f}")


if __name__ == "__main__":
    main()
