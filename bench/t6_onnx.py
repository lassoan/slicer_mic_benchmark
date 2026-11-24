"""Section 6: ONNX Runtime vs PyTorch CPU inference of the MONAIAuto3DSeg network (SegResNetDS,
"Abdominal organs TS2 - quick", 3 mm), on the AI subset of cases.

The same preprocessed input (resampled to the model's 3 mm spacing, intensity-normalized as in the Slicer
extension's inference script) goes through the same MONAI sliding-window inferer; only the network evaluation
differs: torch module vs ONNX Runtime session (CPU execution provider) with the network exported to ONNX
(scripts/export_onnx.py, opset 17, one file used by all environments).

6a single 112x112x144 patch, median of 5, with 1 thread and with all threads (torch and ONNX Runtime)
6b sliding window over each case, all threads (torch and ONNX Runtime)
NPU (arm64 environment only, when the onnxruntime-qnn plugin is installed): the same tasks on the Hexagon NPU
with the QNN execution provider (HTP backend, fp16 precision, no CPU fallback), using an "EP context" model
with the precompiled NPU graph (scripts/npu_probe.py --make-context; compiling takes ~16 min, done once).
Output check: the label maps from ONNX Runtime and torch are compared (Dice) in each run.
"""

import time

import numpy as np

from bench import config, harness
from bench.t2_numpy import load_case, r
from bench.t5_ai import MONAI_DIR, MONAI_MODELS

DEFAULT_REPEATS = 1
ONNX_DIR = config.DATA / "models" / "onnx"
MODEL_NAME = next(iter(MONAI_MODELS))
ONNX_FILE = ONNX_DIR / f"{MODEL_NAME}.onnx"
PATCH_REPEATS = 5
NPU_CTX_FILE = ONNX_DIR / f"{MODEL_NAME}-static-qnn-htp-fp16_ctx.onnx"


def npu_session():
    """ONNX Runtime session on the Hexagon NPU (QNN EP plugin), or None if not available in this environment."""
    try:
        import onnxruntime as ort
        import onnxruntime_qnn
    except ImportError:
        return None
    if not NPU_CTX_FILE.exists():
        return None
    try:
        ort.register_execution_provider_library(onnxruntime_qnn.get_ep_name(), onnxruntime_qnn.get_library_path())
    except Exception:
        pass  # already registered
    npu = [d for d in ort.get_ep_devices()
           if d.ep_name == onnxruntime_qnn.get_ep_name() and d.device.type == ort.OrtHardwareDeviceType.NPU]
    if not npu:
        return None
    so = ort.SessionOptions()
    so.log_severity_level = 3
    so.add_session_config_entry("session.disable_cpu_ep_fallback", "1")
    so.add_provider_for_devices(npu, {"htp_performance_mode": "burst", "enable_htp_fp16_precision": "1"})
    return ort.InferenceSession(str(NPU_CTX_FILE), so)


def load_torch_model():
    import torch
    from monai.bundle import ConfigParser
    ckpt = torch.load(next((MONAI_DIR / MODEL_NAME).rglob("model.pt")), map_location="cpu", weights_only=False)
    cfg = ckpt["config"]
    net = ConfigParser(cfg["network"]).get_parsed_content()
    net.load_state_dict(ckpt["state_dict"], strict=True)
    net.eval()
    return net, cfg


def preprocess(case, cfg):
    """Resample to the model spacing and normalize (range mode + sigmoid, as in the extension's script)."""
    import scipy.ndimage as ndi
    arr, spacing = load_case(case)  # (z, y, x)
    target = cfg["resample_resolution"]
    zoom = [s / t for s, t in zip(spacing, target[::-1])]
    arr = ndi.zoom(arr.astype(np.float32), zoom, order=1)
    a_min, a_max = cfg["intensity_bounds"]
    arr = (arr - a_min) / (a_max - a_min) * 2.0 - 1.0
    arr = 1.0 / (1.0 + np.exp(-arr))
    # network input (batch, channel, x, y, z) as in the MONAI pipeline
    return np.ascontiguousarray(arr.transpose(2, 1, 0)[None, None]).astype(np.float32)


def dice_labels(a, b, n):
    d = []
    for l in range(1, n):
        x, y = a == l, b == l
        s = x.sum() + y.sum()
        if s:
            d.append(2 * np.logical_and(x, y).sum() / s)
    return float(np.mean(d)), float(np.min(d))


def run(runner, cases=None, tasks=None, threads=1, env="unknown"):
    import onnxruntime as ort
    import torch
    from monai.inferers import SlidingWindowInferer

    cases = cases or config.ai_cases()
    harness.set_library_threads(threads)
    net, cfg = load_torch_model()
    roi = cfg["roi_size"]
    n_classes = cfg["output_classes"]

    def ort_session(n):
        so = ort.SessionOptions()
        so.intra_op_num_threads = n
        so.inter_op_num_threads = 1
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        return ort.InferenceSession(str(ONNX_FILE), so, providers=["CPUExecutionProvider"])

    def want(name):
        return tasks is None or any(name.startswith(t) for t in tasks)

    extra = {"onnxruntime": ort.__version__, "providers": ort.get_available_providers()}
    npu = npu_session()
    extra["npu"] = npu is not None
    if npu is not None:
        import onnxruntime_qnn
        extra["onnxruntime_qnn"] = onnxruntime_qnn.__version__
        npu_input = npu.get_inputs()[0].name

    # --- 6a single patch
    if want("6a"):
        x = np.random.default_rng(0).random((1, 1, *roi), dtype=np.float32)
        for n in sorted({1, threads}):
            torch.set_num_threads(n)
            sess = ort_session(n)

            def t_torch():
                with torch.no_grad():
                    y = net(torch.from_numpy(x))
                return {"sum": r(float(y.float().sum()))}

            def t_ort():
                y = sess.run(None, {"input": x})[0]
                return {"sum": r(float(y.sum()))}
            runner.run(f"6a_patch_torch_t{n}", t_torch, repeats=PATCH_REPEATS, warmup=1)
            runner.run(f"6a_patch_onnxruntime_t{n}", t_ort, repeats=PATCH_REPEATS, warmup=1)
        torch.set_num_threads(threads)
        if npu is not None:
            def t_npu():
                y = npu.run(None, {npu_input: x})[0]
                return {"sum": r(float(y.sum()))}
            runner.run("6a_patch_npu_qnn_fp16", t_npu, repeats=PATCH_REPEATS, warmup=1)

    # --- 6b sliding window over each case
    if want("6b"):
        sess = ort_session(threads)
        inferer = SlidingWindowInferer(roi_size=roi, sw_batch_size=1, overlap=0.625, mode="gaussian")

        def ort_predict(t):
            return torch.from_numpy(sess.run(None, {"input": t.numpy()})[0])

        agreement = {}
        for case in cases:
            inp = torch.from_numpy(preprocess(case, cfg))
            out = {}

            def t_torch():
                with torch.no_grad():
                    out["torch"] = inferer(inp, net).argmax(1)[0].numpy().astype(np.uint8)
                return {"labels": int(len(np.unique(out["torch"]))), "fg": int((out["torch"] > 0).sum())}

            def t_ort():
                out["ort"] = inferer(inp, ort_predict).argmax(1)[0].numpy().astype(np.uint8)
                return {"labels": int(len(np.unique(out["ort"]))), "fg": int((out["ort"] > 0).sum())}
            runner.run(f"6b_sliding_window_torch_{case}", t_torch, warmup=0)
            runner.run(f"6b_sliding_window_onnxruntime_{case}", t_ort, warmup=0)
            mean_d, min_d = dice_labels(out["torch"], out["ort"], n_classes)
            agreement[case] = {"dice_mean": round(mean_d, 5), "dice_min": round(min_d, 5),
                               "windows_shape": list(inp.shape)}
            if npu is not None:
                def npu_predict(t):
                    return torch.from_numpy(npu.run(None, {npu_input: t.numpy()})[0])

                def t_npu():
                    out["npu"] = inferer(inp, npu_predict).argmax(1)[0].numpy().astype(np.uint8)
                    return {"labels": int(len(np.unique(out["npu"]))), "fg": int((out["npu"] > 0).sum())}
                runner.run(f"6b_sliding_window_npu_qnn_fp16_{case}", t_npu, warmup=1)
                nd, nmin = dice_labels(out["torch"], out["npu"], n_classes)
                agreement[case].update({"npu_dice_mean": round(nd, 5), "npu_dice_min": round(nmin, 5)})
                print(f"  {case}: Dice NPU vs torch mean {nd:.5f} min {nmin:.5f}")
            print(f"  {case}: input {tuple(inp.shape)}, Dice onnxruntime vs torch mean {mean_d:.5f} min {min_d:.5f}")
        extra["onnx_vs_torch"] = agreement
    return extra
