"""Probe: run the MONAIAuto3DSeg network (ONNX) on the Snapdragon Hexagon NPU with ONNX Runtime + QNN EP plugin.

Usage (arm64 env): python scripts/npu_probe.py [--fallback] [--fp32]
  --fallback  allow nodes that QNN cannot run to fall back to the CPU EP (default: fail instead)
  --fp32      do not request fp16 precision on the HTP (fp32 is normally not supported on the HTP)
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import onnxruntime_qnn

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bench.t6_onnx import ONNX_DIR  # noqa: E402
ONNX_FILE = ONNX_DIR / "abdominal-organs-3mm-v2.0.0-static.onnx"
CTX_FILE = ONNX_DIR / "abdominal-organs-3mm-v2.0.0-static-qnn-htp-fp16_ctx.onnx"


_registered = False


def register():
    global _registered
    if not _registered:
        ort.register_execution_provider_library(onnxruntime_qnn.get_ep_name(), onnxruntime_qnn.get_library_path())
        _registered = True


def npu_session(fallback=False, fp16=True, cache=None, model=None):
    register()
    devices = [d for d in ort.get_ep_devices() if d.ep_name == onnxruntime_qnn.get_ep_name()]
    npu = [d for d in devices if d.device.type == ort.OrtHardwareDeviceType.NPU]
    if not npu:
        raise RuntimeError(f"No NPU device; QNN devices: {[(d.device.type, d.device.vendor) for d in devices]}")
    so = ort.SessionOptions()
    so.log_severity_level = 2
    if not fallback:
        so.add_session_config_entry("session.disable_cpu_ep_fallback", "1")
    if cache:
        # Write the compiled NPU graph (QNN context binary) to an "EP context" ONNX model that loads in seconds
        so.add_session_config_entry("ep.context_enable", "1")
        so.add_session_config_entry("ep.context_file_path", str(cache))
        so.add_session_config_entry("ep.context_embed_mode", "1")
    opts = {"htp_performance_mode": "burst"}
    if fp16:
        opts["enable_htp_fp16_precision"] = "1"
    so.add_provider_for_devices(npu, opts)
    return ort.InferenceSession(str(model or ONNX_FILE), so)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fallback", action="store_true")
    p.add_argument("--fp32", action="store_true")
    p.add_argument("--make-context", action="store_true", help=f"write {CTX_FILE.name} and exit")
    args = p.parse_args()
    print("onnxruntime", ort.__version__, "qnn plugin", onnxruntime_qnn.__version__)
    register()
    for d in ort.get_ep_devices():
        print(f"  device: ep={d.ep_name} type={d.device.type} vendor={d.device.vendor} meta={dict(d.device.metadata)}")
    t0 = time.perf_counter()
    if args.make_context:
        npu_session(args.fallback, not args.fp32, cache=CTX_FILE)
        print(f"context model written in {time.perf_counter() - t0:.1f} s: {CTX_FILE} ({CTX_FILE.stat().st_size / 1e6:.1f} MB)")
        t0 = time.perf_counter()
        sess = npu_session(args.fallback, not args.fp32, model=CTX_FILE)
        print(f"context model loaded in {time.perf_counter() - t0:.1f} s")
        return
    sess = npu_session(args.fallback, not args.fp32)
    print(f"session created in {time.perf_counter() - t0:.1f} s, providers {sess.get_providers()}")
    x = np.random.default_rng(0).random((1, 1, 112, 112, 144), dtype=np.float32)
    times = []
    for i in range(4):
        t0 = time.perf_counter()
        y = sess.run(None, {"input": x})[0]
        times.append(time.perf_counter() - t0)
    print(f"NPU patch times: {[round(t, 3) for t in times]}")
    cpu = ort.InferenceSession(str(ONNX_FILE), providers=["CPUExecutionProvider"])
    ref = cpu.run(None, {"input": x})[0]
    print(f"max abs diff vs CPU {np.abs(y - ref).max():.3e}, argmax agreement {(y.argmax(1) == ref.argmax(1)).mean():.5f}")


if __name__ == "__main__":
    main()
