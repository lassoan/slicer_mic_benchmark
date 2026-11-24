"""Timing, thread control, environment metadata and result output for the benchmark sections."""

import gc
import importlib.metadata
import json
import os
import platform
import statistics
import sys
import sysconfig
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

THREAD_ENV_VARS = ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS",
                   "VECLIB_MAXIMUM_THREADS", "ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS", "nnUNet_n_proc_DA"]

PACKAGES = ["numpy", "scipy", "simpleitk", "vtk", "pynrrd", "nibabel", "pydicom", "torch", "monai",
            "TotalSegmentator", "nnunetv2", "scikit-image", "connected-components-3d"]


def set_thread_env(threads):
    """Must be called before numpy, SimpleITK, VTK or torch are imported."""
    for var in THREAD_ENV_VARS:
        os.environ[var] = str(threads)


def set_library_threads(threads):
    """Set thread counts in libraries that have an API for it (call after importing them)."""
    applied = {}
    if "SimpleITK" in sys.modules:
        import SimpleITK as sitk
        sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(threads)
        applied["SimpleITK"] = sitk.ProcessObject.GetGlobalDefaultNumberOfThreads()
    if "vtkmodules" in sys.modules:
        try:
            from vtkmodules.vtkCommonCore import vtkSMPTools, vtkMultiThreader
            # Official VTK wheels default to the Sequential SMP backend; use STDThread when threads > 1
            vtkSMPTools.SetBackend("STDThread" if threads > 1 else "Sequential")
            vtkSMPTools.Initialize(threads)
            vtkMultiThreader.SetGlobalMaximumNumberOfThreads(threads)
            vtkMultiThreader.SetGlobalDefaultNumberOfThreads(threads)
            applied["vtk_smp_backend"] = vtkSMPTools.GetBackend()
            applied["vtk_smp_threads"] = vtkSMPTools.GetEstimatedNumberOfThreads()
        except ImportError:
            pass
    if "torch" in sys.modules:
        import torch
        torch.set_num_threads(threads)
        applied["torch"] = torch.get_num_threads()
    return applied


def pe_machine_type(path):
    """Return 'x64', 'arm64', 'arm64ec', 'arm64x' or 'other' for a PE file (DLL, PYD, EXE)."""
    import pefile
    try:
        pe = pefile.PE(str(path), fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_LOAD_CONFIG"]])
        chpe = 0
        lc = getattr(pe, "DIRECTORY_ENTRY_LOAD_CONFIG", None)
        if lc is not None:
            chpe = getattr(lc.struct, "CHPEMetadataPointer", 0) or 0
        m = pe.FILE_HEADER.Machine
        pe.close()
    except Exception:
        return "unknown"
    if m == 0x8664:
        return "arm64ec" if chpe else "x64"
    if m == 0xAA64:
        return "arm64x" if chpe else "arm64"
    return f"other(0x{m:x})"


def loaded_module_architectures():
    """Architectures of the DLLs/PYDs loaded in this process, excluding Windows system files."""
    import psutil
    paths = set()
    for m in psutil.Process().memory_maps(grouped=True):
        p = m.path
        if p.lower().endswith((".dll", ".pyd", ".exe")):
            paths.add(p)
    windir = os.environ.get("WINDIR", r"C:\Windows").lower()
    result = {}
    for p in sorted(paths):
        if p.lower().startswith(windir):
            continue
        result[p] = pe_machine_type(p)
    summary = {}
    for arch in result.values():
        summary[arch] = summary.get(arch, 0) + 1
    return {"summary": summary, "modules": result}


def environment_metadata():
    import psutil
    versions = {}
    for p in PACKAGES:
        try:
            versions[p] = importlib.metadata.version(p)
        except importlib.metadata.PackageNotFoundError:
            pass
    cpu = platform.processor()
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        cpu = winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
    except OSError:
        pass
    return {
        "env": os.environ.get("BENCH_ENV", "unknown"),
        "python": sys.version,
        "executable": sys.executable,
        "python_platform": sysconfig.get_platform(),
        "machine": platform.machine(),
        "windows": platform.version(),
        "cpu": cpu,
        "logical_cpus": psutil.cpu_count(),
        "memory_gb": round(psutil.virtual_memory().total / 2**30, 1),
        "packages": versions,
        "python_exe_arch": pe_machine_type(sys.executable),
        "python_dll_arch": pe_machine_type(Path(sys.base_prefix) / ("bin" if (Path(sys.base_prefix) / "bin" / "python312.dll").exists() else "") / "python312.dll"),
        "system": _system_info(),
    }


def _system_info():
    """Computer description (bench/sysinfo.py): OS, CPU cores and features, RAM, GPU, NPU, disk, power state.
    Collected when the results are saved, so the power state is the one at the end of the run."""
    from bench import sysinfo
    try:
        return sysinfo.system_info()
    except Exception as e:  # never lose the benchmark results because of the description
        return {"error": f"{type(e).__name__}: {e}"}


class Runner:
    """Runs tasks with warm-up and repeats and collects results."""

    def __init__(self, section, threads, repeats, warmup=1, verbose=True):
        self.section = section
        self.threads = threads
        self.repeats = repeats
        self.warmup = warmup
        self.verbose = verbose
        self.results = {}

    def run(self, name, fn, repeats=None, warmup=None):
        """fn() performs the task and returns a dict signature (small JSON-serializable result check)."""
        repeats = self.repeats if repeats is None else repeats
        warmup = self.warmup if warmup is None else warmup
        times = []
        first = None
        signature = None
        for i in range(warmup + repeats):
            gc.collect()
            t0 = time.perf_counter()
            sig = fn()
            dt = time.perf_counter() - t0
            if i == 0:
                first = dt
                signature = sig
            if i >= warmup:
                times.append(dt)
        med = statistics.median(times) if times else first
        self.results[name] = {"median_s": med, "times_s": times, "first_s": first, "signature": signature}
        if self.verbose:
            print(f"  {name:40s} median {med:9.4f} s  (first {first:.4f} s, n={len(times)})", flush=True)
        return signature

    def save(self, out_path, extra=None):
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "section": self.section,
            "threads": self.threads,
            "repeats": self.repeats,
            "warmup": self.warmup,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "environment": environment_metadata(),
            "loaded_modules": loaded_module_architectures(),
            "tasks": self.results,
        }
        if extra:
            data.update(extra)
        # results are published: no paths with user or computer names (bench/privacy.py)
        from bench.privacy import scrub
        data = json.loads(json.dumps(data, default=_json_default))
        out_path.write_text(json.dumps(scrub(data), indent=1))
        print(f"Results written to {out_path}")


def _json_default(o):
    import numpy as np
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o))
