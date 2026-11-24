"""Make a fixed-shape copy of an ONNX model (batch size 1, all tensor shapes inferred), needed by the QNN (NPU)
execution provider. Run in the tools environment (onnx, onnxruntime).

Usage: python scripts/make_static_onnx.py <model.onnx> <model-static.onnx>
"""

import sys

import onnx
from onnxruntime.tools.onnx_model_utils import fix_output_shapes, make_dim_param_fixed


def main():
    src, dst = sys.argv[1], sys.argv[2]
    model = onnx.load(src)
    make_dim_param_fixed(model.graph, "batch", 1)
    fix_output_shapes(model)
    model = onnx.shape_inference.infer_shapes(model)
    onnx.save(model, dst)
    print(f"fixed-shape model written: {dst}")


if __name__ == "__main__":
    main()
