"""Describe the computer a benchmark ran on: OS, architecture, CPU, RAM, GPU, NPU, storage, power and Python.

Standard library only (no psutil needed). Works on Windows (primary target), Linux and macOS; anything that
cannot be determined is left out instead of raising.

    python bench/sysinfo.py           # human-readable summary
    python bench/sysinfo.py --json    # full details as JSON
    python bench/sysinfo.py --short   # compact id, e.g. win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_..._npu_hexagon

    from bench.sysinfo import system_info, summary_line, short_id
"""

import ctypes
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

PE_MACHINES = {0x14C: "x86", 0x8664: "x64", 0xAA64: "arm64", 0x1C4: "arm"}
ARCH_ALIASES = {"amd64": "x64", "x86_64": "x64", "x64": "x64", "arm64": "arm64", "aarch64": "arm64",
                "i386": "x86", "i686": "x86", "x86": "x86", "win32": "x86"}
SMBIOS_MEMORY_TYPES = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 27: "LPDDR", 28: "LPDDR2", 29: "LPDDR3",
                       30: "LPDDR4", 32: "HBM", 33: "HBM2", 34: "DDR5", 35: "LPDDR5"}
# Windows 11 power mode (Settings > System > Power), stored as an overlay scheme on top of the power plan
WINDOWS_POWER_MODES = {"00000000-0000-0000-0000-000000000000": "Balanced",
                       "961cc777-2547-4f9d-8174-7d86181b8a7a": "Best power efficiency",
                       "ded574b5-45a0-4f42-8737-46345c09c238": "Best performance"}
LINUX_ACCEL_DRIVERS = {"intel_vpu": "Intel NPU", "amdxdna": "AMD XDNA NPU", "qaic": "Qualcomm Cloud AI",
                       "habanalabs": "Intel Gaudi", "ivpu": "Intel NPU"}


def _norm_arch(name):
    return ARCH_ALIASES.get((name or "").lower(), (name or "").lower() or None)


def _run(cmd, timeout=60):
    """Run a command and return its stdout as text, or None if it fails or does not exist."""
    if shutil.which(cmd[0]) is None:
        return None
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout, encoding="utf-8", errors="replace",
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return p.stdout if p.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def _gb(nbytes, digits=1):
    return round(nbytes / 2**30, digits) if nbytes else None


def _clean(d):
    """Drop None/empty values (recursively) so the output only has what was found."""
    if isinstance(d, dict):
        return {k: _clean(v) for k, v in d.items() if v not in (None, "", [], {})}
    if isinstance(d, list):
        return [_clean(v) for v in d]
    return d


# ---------------------------------------------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------------------------------------------

_WIN_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$r = [ordered]@{}
$r.os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture
$r.cs = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, SystemFamily, TotalPhysicalMemory
$r.cpu = @(Get-CimInstance Win32_Processor | Select-Object Name, Manufacturer, NumberOfCores,
    NumberOfLogicalProcessors, MaxClockSpeed, L2CacheSize, L3CacheSize)
$r.mem = @(Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity, Speed, ConfiguredClockSpeed,
    SMBIOSMemoryType, Manufacturer, PartNumber)
$r.gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name, AdapterCompatibility, DriverVersion,
    @{n='DriverDate'; e={ if ($_.DriverDate) { $_.DriverDate.ToString('yyyy-MM-dd') } }}, AdapterRAM, PNPDeviceID)
$r.npu = @(Get-CimInstance Win32_PnPEntity -Filter "PNPClass='ComputeAccelerator' OR Name LIKE 'NPU%' OR Name LIKE '% NPU%' OR Name LIKE '%AI Boost%' OR Name LIKE '%Neural Processing%'" |
    Select-Object Name, Manufacturer, PNPClass, PNPDeviceID, Status)
$r.accel_drivers = @(Get-CimInstance Win32_PnPSignedDriver -Filter "DeviceClass='COMPUTEACCELERATOR'" |
    Select-Object DeviceID, DriverVersion, @{n='DriverDate'; e={ if ($_.DriverDate) { $_.DriverDate.ToString('yyyy-MM-dd') } }})
$sysdisk = (Get-Partition -DriveLetter $env:SystemDrive.Substring(0, 1)).DiskNumber
$r.disk = @(Get-PhysicalDisk | Select-Object FriendlyName, @{n='MediaType'; e={"$($_.MediaType)"}},
    @{n='BusType'; e={"$($_.BusType)"}}, Size, @{n='System'; e={ "$($_.DeviceId)" -eq "$sysdisk" }})
$r | ConvertTo-Json -Depth 4 -Compress
"""


def _win_cim():
    out = _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                "-Command", _WIN_PS], timeout=120)
    try:
        return json.loads(out) if out else {}
    except json.JSONDecodeError:
        return {}


def _as_list(v):
    return [] if v is None else v if isinstance(v, list) else [v]


def _win_reg(path, names, root=None):
    import winreg
    out = {}
    try:
        with winreg.OpenKey(root or winreg.HKEY_LOCAL_MACHINE, path) as k:
            for n in names:
                try:
                    out[n] = winreg.QueryValueEx(k, n)[0]
                except OSError:
                    pass
    except OSError:
        pass
    return out


def _win_native_arch():
    """Native machine architecture, also when this process runs emulated (x64 on ARM64, x86 on x64)."""
    try:
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.IsWow64Process2.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_ushort),
                                        ctypes.POINTER(ctypes.c_ushort)]
        proc, native = ctypes.c_ushort(), ctypes.c_ushort()
        if k32.IsWow64Process2(k32.GetCurrentProcess(), ctypes.byref(proc), ctypes.byref(native)) \
                and native.value in PE_MACHINES:
            return PE_MACHINES[native.value]
    except (AttributeError, OSError):
        pass
    # The system-wide value is not changed for emulated processes (unlike the process environment variable)
    v = _win_reg(r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", ["PROCESSOR_ARCHITECTURE"])
    return _norm_arch(v.get("PROCESSOR_ARCHITECTURE") or os.environ.get("PROCESSOR_ARCHITEW6432")
                      or os.environ.get("PROCESSOR_ARCHITECTURE"))


def _win_core_topology():
    """Physical cores by efficiency class via GetLogicalProcessorInformationEx (higher class = faster cores)."""
    k32 = ctypes.windll.kernel32
    size = ctypes.c_ulong(0)
    k32.GetLogicalProcessorInformationEx(0, None, ctypes.byref(size))  # RelationProcessorCore = 0
    buf = ctypes.create_string_buffer(size.value)
    if not k32.GetLogicalProcessorInformationEx(0, buf, ctypes.byref(size)):
        return None
    raw, off, classes, smt = buf.raw, 0, {}, False
    ptr = ctypes.sizeof(ctypes.c_void_p)
    while off < size.value:
        rec_size = int.from_bytes(raw[off + 4:off + 8], "little")
        flags, eff = raw[off + 8], raw[off + 9]
        group_count = int.from_bytes(raw[off + 30:off + 32], "little")
        threads = 0
        for g in range(group_count):  # GROUP_AFFINITY array starts at offset 32, each entry ptr + 8 bytes
            mask_off = off + 32 + g * (ptr + 8)
            threads += bin(int.from_bytes(raw[mask_off:mask_off + ptr], "little")).count("1")
        smt = smt or bool(flags & 1)
        c = classes.setdefault(eff, {"cores": 0, "threads": 0})
        c["cores"] += 1
        c["threads"] += threads
        off += rec_size
    return {"physical_cores": sum(c["cores"] for c in classes.values()),
            "logical_cpus": sum(c["threads"] for c in classes.values()),
            "smt": smt, "core_classes": _core_classes(classes)}


def _core_classes(classes):
    """{rank: {cores, threads}} -> list from fastest to slowest; None if all cores are the same kind."""
    if len(classes) < 2:
        return None
    names = ["performance", "efficiency"] if len(classes) == 2 else None
    ranked = sorted(classes.items(), reverse=True)
    return [dict(kind=names[i] if names else f"class {rank}", **c) for i, (rank, c) in enumerate(ranked)]


def _win_cpu_features():
    """Instruction set extensions as reported to this process (an emulated process sees the emulator's set)."""
    feats = {"sse4_2": 38, "avx": 39, "avx2": 40, "avx512f": 41,
             "neon": 29, "crypto": 30, "crc32": 31, "atomics": 34, "dotprod": 43, "jscvt": 44, "lrcpc": 45,
             "sve": 46, "sve2": 47}
    try:
        f = ctypes.windll.kernel32.IsProcessorFeaturePresent
        return [name for name, pf in feats.items() if f(pf)]
    except (AttributeError, OSError):
        return None


def _win_gpu_memory():
    """Dedicated GPU memory by adapter name from the display class registry key (Win32_VideoController caps at 4 GB)."""
    import winreg
    cls = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
    result = {}
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cls) as k:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(k, i)
                except OSError:
                    break
                i += 1
                v = _win_reg(cls + "\\" + sub, ["DriverDesc", "HardwareInformation.qwMemorySize",
                                                "HardwareInformation.MemorySize"])
                mem = v.get("HardwareInformation.qwMemorySize") or v.get("HardwareInformation.MemorySize")
                if isinstance(mem, bytes):
                    mem = int.from_bytes(mem, "little")
                if v.get("DriverDesc") and mem:
                    result[v["DriverDesc"]] = mem
    except OSError:
        pass
    return result


def _win_power():
    out = {}
    try:
        class SPS(ctypes.Structure):
            _fields_ = [("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte),
                        ("BatteryLifePercent", ctypes.c_byte), ("SystemStatusFlag", ctypes.c_byte),
                        ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]
        s = SPS()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):
            out["source"] = {0: "battery", 1: "AC"}.get(s.ACLineStatus)
            if not s.BatteryFlag & 128 and s.BatteryLifePercent != -1:
                out["battery_percent"] = s.BatteryLifePercent
    except (AttributeError, OSError):
        pass
    plan = _run(["powercfg", "/getactivescheme"], timeout=15)
    m = re.search(r"\((.+)\)\s*$", plan or "")
    if m:
        out["plan"] = m.group(1)
    overlay = _win_reg(r"SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes",
                       ["ActiveOverlayAcPowerScheme", "ActiveOverlayDcPowerScheme"])
    key = "ActiveOverlayDcPowerScheme" if out.get("source") == "battery" else "ActiveOverlayAcPowerScheme"
    if key in overlay:
        out["mode"] = WINDOWS_POWER_MODES.get(overlay[key].lower(), overlay[key])
    return out


def _windows():
    cim = _win_cim()
    cv = _win_reg(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
                  ["ProductName", "DisplayVersion", "CurrentBuild", "UBR", "EditionID"])
    osinfo = cim.get("os") or {}
    build = cv.get("CurrentBuild") or osinfo.get("BuildNumber")
    name = (osinfo.get("Caption") or cv.get("ProductName") or "Windows").replace("Microsoft ", "")
    if build and int(build) >= 22000:  # the registry ProductName still says "Windows 10" on Windows 11
        name = name.replace("Windows 10", "Windows 11")
    result = {"os": {"name": name, "version": cv.get("DisplayVersion"),
                     "build": f"{build}.{cv['UBR']}" if build and "UBR" in cv else build,
                     "kernel": platform.version()}}

    cs = cim.get("cs") or {}
    result["system"] = {"manufacturer": cs.get("Manufacturer"), "model": cs.get("Model"),
                        "family": cs.get("SystemFamily")}

    cpus = _as_list(cim.get("cpu"))
    reg_cpu = _win_reg(r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
                       ["ProcessorNameString", "VendorIdentifier", "~MHz", "Identifier"])
    cpu = {"name": (cpus[0].get("Name") if cpus else None) or reg_cpu.get("ProcessorNameString"),
           "vendor": (cpus[0].get("Manufacturer") if cpus else None) or reg_cpu.get("VendorIdentifier"),
           "identifier": reg_cpu.get("Identifier"),
           "sockets": len(cpus) or None,
           "physical_cores": sum(c.get("NumberOfCores") or 0 for c in cpus) or None,
           "logical_cpus": sum(c.get("NumberOfLogicalProcessors") or 0 for c in cpus) or os.cpu_count(),
           "max_mhz": (cpus[0].get("MaxClockSpeed") if cpus else None) or reg_cpu.get("~MHz"),
           "l2_cache_kb": sum(c.get("L2CacheSize") or 0 for c in cpus) or None,
           "l3_cache_kb": sum(c.get("L3CacheSize") or 0 for c in cpus) or None}
    try:
        topo = _win_core_topology()
        if topo:
            cpu.update(topo)
    except (AttributeError, OSError):
        pass
    cpu["features"] = _win_cpu_features()
    cpu["name"] = re.sub(r"\s+", " ", cpu["name"]).strip() if cpu["name"] else None
    result["cpu"] = cpu

    mods = _as_list(cim.get("mem"))
    total = None
    try:
        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + \
                       [(n, ctypes.c_ulonglong) for n in ("total", "avail", "tpf", "apf", "tv", "av", "aev")]
        ms = MS(dwLength=ctypes.sizeof(MS))
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
            total = ms.total
    except (AttributeError, OSError):
        pass
    installed = sum(int(m.get("Capacity") or 0) for m in mods)
    types = {SMBIOS_MEMORY_TYPES.get(m.get("SMBIOSMemoryType")) for m in mods} - {None}
    speeds = {m.get("ConfiguredClockSpeed") or m.get("Speed") for m in mods} - {None, 0}
    result["memory"] = {"total_gb": _gb(installed) or _gb(total), "usable_gb": _gb(total),
                        "type": "/".join(sorted(types)) or None,
                        "speed_mts": max(speeds) if speeds else None,
                        "modules": len(mods) or None,
                        "manufacturer": "/".join(sorted({(m.get("Manufacturer") or "").strip() for m in mods} - {""}))}

    gpu_mem = _win_gpu_memory()
    gpus = []
    for g in _as_list(cim.get("gpu")):
        name = (g.get("Name") or "").strip()
        dedicated = gpu_mem.get(name) or g.get("AdapterRAM")
        gpus.append({"name": name, "vendor": g.get("AdapterCompatibility"),
                     "driver": g.get("DriverVersion"), "driver_date": g.get("DriverDate"),
                     "dedicated_memory_gb": _gb(dedicated),
                     "virtual": bool(re.search(r"Basic Display|Remote Display|Hyper-V|Virtual|Parsec|Indirect",
                                               name, re.I)) or None})
    result["gpus"] = _nvidia_smi(gpus)

    drivers = {d.get("DeviceID"): d for d in _as_list(cim.get("accel_drivers"))}
    npus = []
    for n in _as_list(cim.get("npu")):
        d = drivers.get(n.get("PNPDeviceID"), {})
        npus.append({"name": (n.get("Name") or "").strip(), "vendor": n.get("Manufacturer"),
                     "device_class": n.get("PNPClass"), "status": n.get("Status"),
                     "driver": d.get("DriverVersion"), "driver_date": d.get("DriverDate")})
    result["npus"] = npus

    result["storage"] = [{"name": d.get("FriendlyName"), "media": d.get("MediaType"), "bus": d.get("BusType"),
                          "size_gb": _gb(d.get("Size"), 0), "system_disk": d.get("System") or None}
                         for d in _as_list(cim.get("disk"))]
    result["power"] = _win_power()
    result["_native_arch"] = _win_native_arch()
    return result


# ---------------------------------------------------------------------------------------------------------------
# Linux
# ---------------------------------------------------------------------------------------------------------------

def _linux():
    result = {}
    osr = {}
    try:
        osr = platform.freedesktop_os_release()
    except (AttributeError, OSError):
        for line in (_read("/etc/os-release") or "").splitlines():
            k, _, v = line.partition("=")
            osr[k] = v.strip('"')
    result["os"] = {"name": osr.get("PRETTY_NAME") or "Linux", "version": osr.get("VERSION_ID"),
                    "kernel": platform.release()}
    if os.environ.get("WSL_DISTRO_NAME") or "microsoft" in platform.release().lower():
        result["os"]["wsl"] = True
    dmi = "/sys/class/dmi/id/"
    result["system"] = {"manufacturer": _read(dmi + "sys_vendor"), "model": _read(dmi + "product_name"),
                        "family": _read(dmi + "product_family")}
    if not result["system"]["model"]:
        result["system"]["model"] = (_read("/sys/firmware/devicetree/base/model") or "").rstrip("\x00") or None

    lscpu = {}
    for line in (_run(["lscpu"]) or "").splitlines():
        k, _, v = line.partition(":")
        lscpu.setdefault(k.strip(), []).append(v.strip())
    cpuinfo = _read("/proc/cpuinfo") or ""
    names = list(dict.fromkeys(lscpu.get("Model name", []) or re.findall(r"^model name\s*:\s*(.+)$", cpuinfo, re.M)))
    flags = set((re.search(r"^(?:flags|Features)\s*:\s*(.+)$", cpuinfo, re.M) or [None, ""])[1].split()) \
        or set(" ".join(lscpu.get("Flags", [])).split())
    wanted = ["sse4_2", "avx", "avx2", "fma", "avx512f", "avx512_bf16", "amx_tile",
              "asimd", "asimddp", "i8mm", "bf16", "sve", "sve2", "sme"]

    cores, classes = set(), {}
    base = Path("/sys/devices/system/cpu")
    for c in base.glob("cpu[0-9]*"):
        pkg, core = _read(c / "topology/physical_package_id"), _read(c / "topology/core_id")
        if core is None:
            continue
        cores.add((pkg, core))
        cap = _read(c / "cpu_capacity")  # ARM big.LITTLE; Intel hybrid uses the cpu_core/cpu_atom PMUs below
        if cap:
            classes.setdefault(int(cap), {"cores": set(), "threads": 0})
            classes[int(cap)]["cores"].add((pkg, core))
            classes[int(cap)]["threads"] += 1
    if not classes and (base / "types").exists() is False and Path("/sys/devices/cpu_core/cpus").exists():
        for rank, pmu in ((1, "cpu_core"), (0, "cpu_atom")):
            cpus = _read(f"/sys/devices/{pmu}/cpus")
            if cpus:
                n = sum(int(b) - int(a) + 1 if b else 1 for a, _, b in (r.partition("-") for r in cpus.split(",")))
                classes[rank] = {"cores": set(range(n)), "threads": n}  # thread counts; cores approximate
    max_khz = [int(v) for v in (_read(p) for p in base.glob("cpu*/cpufreq/cpuinfo_max_freq")) if v]
    result["cpu"] = {
        "name": " + ".join(names) or platform.processor() or None,
        "vendor": (lscpu.get("Vendor ID") or [None])[0],
        "sockets": len({p for p, _ in cores}) or None,
        "physical_cores": len(cores) or None,
        "logical_cpus": os.cpu_count(),
        "max_mhz": round(max(max_khz) / 1000) if max_khz else
        (round(float(lscpu["CPU max MHz"][0])) if "CPU max MHz" in lscpu else None),
        "core_classes": _core_classes({k: {"cores": len(v["cores"]), "threads": v["threads"]}
                                       for k, v in classes.items()}),
        "features": [f for f in wanted if f in flags] or None}

    mem = dict(re.findall(r"^(\w+):\s+(\d+) kB", _read("/proc/meminfo") or "", re.M))
    result["memory"] = {"total_gb": _gb(int(mem["MemTotal"]) * 1024) if "MemTotal" in mem else None}

    gpus = []
    for line in (_run(["lspci", "-mm"]) or "").splitlines():
        parts = re.findall(r'"([^"]*)"', line)
        if len(parts) >= 3 and re.search(r"VGA|3D|Display", parts[0]):
            gpus.append({"name": parts[2], "vendor": parts[1]})
    if not gpus:
        for card in sorted(Path("/sys/class/drm").glob("card[0-9]")):
            drv = (card / "device/driver")
            gpus.append({"name": _read(card / "device/product_name") or card.name,
                         "driver_module": drv.resolve().name if drv.exists() else None})
    result["gpus"] = _nvidia_smi(gpus)

    npus = []
    for acc in sorted(Path("/sys/class/accel").glob("accel*")):
        drv = acc / "device/driver"
        drv_name = drv.resolve().name if drv.exists() else None
        npus.append({"name": LINUX_ACCEL_DRIVERS.get(drv_name, drv_name or acc.name), "driver_module": drv_name})
    result["npus"] = npus

    power = {}
    for ps in Path("/sys/class/power_supply").glob("*"):
        if _read(ps / "type") == "Mains":
            power["source"] = "AC" if _read(ps / "online") == "1" else "battery"
    power["mode"] = _read("/sys/firmware/acpi/platform_profile")
    power["governor"] = _read(base / "cpu0/cpufreq/scaling_governor")
    result["power"] = power
    return result


# ---------------------------------------------------------------------------------------------------------------
# macOS
# ---------------------------------------------------------------------------------------------------------------

def _sysctl(*names):
    out = {}
    for n in names:
        v = _run(["sysctl", "-n", n], timeout=10)
        if v is not None and v.strip():
            v = v.strip()
            out[n] = int(v) if v.isdigit() else v
    return out


def _macos():
    s = _sysctl("machdep.cpu.brand_string", "hw.model", "hw.physicalcpu", "hw.logicalcpu", "hw.memsize",
                "hw.nperflevels", "hw.cpufrequency_max", "sysctl.proc_translated", "hw.optional.arm64",
                "hw.perflevel0.physicalcpu", "hw.perflevel0.logicalcpu", "hw.perflevel0.name",
                "hw.perflevel1.physicalcpu", "hw.perflevel1.logicalcpu", "hw.perflevel1.name",
                "hw.optional.avx2_0", "hw.optional.avx512f", "hw.optional.arm.FEAT_DotProd",
                "hw.optional.arm.FEAT_I8MM", "hw.optional.arm.FEAT_BF16", "hw.optional.arm.FEAT_SME")
    result = {"os": {"name": f"macOS {platform.mac_ver()[0]}", "kernel": platform.release()},
              "system": {"manufacturer": "Apple", "model": s.get("hw.model")}}
    classes = None
    if s.get("hw.nperflevels", 1) > 1:
        classes = [{"kind": s.get(f"hw.perflevel{i}.name", f"level {i}").lower(),
                    "cores": s.get(f"hw.perflevel{i}.physicalcpu"), "threads": s.get(f"hw.perflevel{i}.logicalcpu")}
                   for i in range(s["hw.nperflevels"])]
    feats = {"avx2": "hw.optional.avx2_0", "avx512f": "hw.optional.avx512f", "dotprod": "hw.optional.arm.FEAT_DotProd",
             "i8mm": "hw.optional.arm.FEAT_I8MM", "bf16": "hw.optional.arm.FEAT_BF16", "sme": "hw.optional.arm.FEAT_SME"}
    result["cpu"] = {"name": s.get("machdep.cpu.brand_string"), "physical_cores": s.get("hw.physicalcpu"),
                     "logical_cpus": s.get("hw.logicalcpu"),
                     "max_mhz": round(s["hw.cpufrequency_max"] / 1e6) if "hw.cpufrequency_max" in s else None,
                     "core_classes": classes, "features": [f for f, k in feats.items() if s.get(k) == 1] or None}
    result["memory"] = {"total_gb": _gb(s.get("hw.memsize"))}
    gpus = []
    try:
        sp = json.loads(_run(["system_profiler", "SPDisplaysDataType", "-json"], timeout=60) or "{}")
        for g in sp.get("SPDisplaysDataType", []):
            gpus.append({"name": g.get("sppci_model"), "vendor": g.get("spdisplays_vendor"),
                         "gpu_cores": g.get("sppci_cores"),
                         "dedicated_memory": g.get("spdisplays_vram") or g.get("spdisplays_vram_shared")})
    except json.JSONDecodeError:
        pass
    result["gpus"] = gpus
    native_arm = s.get("hw.optional.arm64") == 1 or s.get("sysctl.proc_translated") == 1
    result["npus"] = [{"name": "Apple Neural Engine"}] if native_arm else []
    batt = _run(["pmset", "-g", "batt"], timeout=10) or ""
    result["power"] = {"source": "AC" if "AC Power" in batt else "battery" if "Battery Power" in batt else None}
    result["_native_arch"] = "arm64" if native_arm else None
    return result


# ---------------------------------------------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------------------------------------------

def _nvidia_smi(gpus):
    """Add exact memory and driver for NVIDIA GPUs when nvidia-smi is available."""
    out = _run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version,compute_cap",
                "--format=csv,noheader,nounits"], timeout=30)
    for line in (out or "").splitlines():
        name, mem, drv, cc = [x.strip() for x in line.split(",")] + [None] * (4 - len(line.split(",")))
        match = next((g for g in gpus if name and name in (g.get("name") or "")), None)
        if match is None:
            match = {"name": name, "vendor": "NVIDIA"}
            gpus.append(match)
        match.update({"dedicated_memory_gb": round(int(mem) / 1024, 1) if mem and mem.isdigit() else None,
                      "nvidia_driver": drv, "cuda_compute_capability": cc})
    return gpus


def pe_architecture(path):
    """'x64', 'arm64', 'arm64ec' (x64 header + CHPE metadata), 'arm64x', 'x86' for a Windows PE file, or None."""
    import struct
    try:
        with open(path, "rb") as f:
            data = f.read()
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        machine, nsec, _, _, _, opt_size = struct.unpack_from("<HHIIIH", data, pe + 4)
        opt = pe + 24
        chpe = 0
        if struct.unpack_from("<H", data, opt)[0] == 0x20B:  # PE32+: data directory 10 = load config
            rva, size = struct.unpack_from("<II", data, opt + 112 + 10 * 8)
            for i in range(nsec):  # map the RVA to a file offset via the section table
                s = opt + opt_size + i * 40
                vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, s + 8)
                if rva and vaddr <= rva < vaddr + max(vsize, rawsize):
                    lc = rawptr + rva - vaddr
                    if struct.unpack_from("<I", data, lc)[0] > 0xC8:
                        chpe = struct.unpack_from("<Q", data, lc + 0xC8)[0]
                    break
    except (OSError, struct.error):
        return None
    arch = PE_MACHINES.get(machine)
    if chpe and arch == "x64":
        return "arm64ec"
    if chpe and arch == "arm64":
        return "arm64x"
    return arch


def _python_dll():
    try:
        buf = ctypes.create_unicode_buffer(32768)
        ctypes.windll.kernel32.GetModuleFileNameW(ctypes.c_void_p(sys.dllhandle), buf, len(buf))
        return buf.value or None
    except (AttributeError, OSError):
        return None


def _process_arch():
    plat = sysconfig.get_platform()  # e.g. win-amd64, win-arm64, linux-x86_64, macosx-11.0-arm64
    arch = _norm_arch(plat.rsplit("-", 1)[-1]) if plat != "win32" else "x86"
    if sys.platform == "win32" and arch == "x64":  # an ARM64EC build reports itself exactly like x64
        dll = _python_dll()
        if dll and pe_architecture(dll) == "arm64ec":
            return "arm64ec"
    return arch


def system_info():
    """Return a dict describing this computer. Keys: os, system, architecture, cpu, memory, gpus, npus,
    storage (Windows), power, python. Missing values are omitted."""
    system = platform.system()
    collectors = {"Windows": _windows, "Linux": _linux, "Darwin": _macos}
    try:
        info = collectors.get(system, lambda: {})()
    except Exception as e:  # keep going with the generic information
        info = {"error": f"{type(e).__name__}: {e}"}
    info.setdefault("os", {"name": f"{system} {platform.release()}"})
    info.setdefault("cpu", {"name": platform.processor() or None, "logical_cpus": os.cpu_count()})

    process = _process_arch()
    native = info.pop("_native_arch", None) or _norm_arch(platform.machine())
    # arm64ec on arm64: Python itself runs natively, x64 extension modules it loads are emulated
    emulated = None if not (native and process) else \
        "partly" if (native, process) == ("arm64", "arm64ec") else native != process
    info["architecture"] = {"machine": native, "python_process": process, "emulated": emulated}
    info["python"] = {"version": platform.python_version(), "implementation": platform.python_implementation(),
                      "compiler": platform.python_compiler(), "platform": sysconfig.get_platform(),
                      "executable": sys.executable,
                      "free_threaded": bool(sysconfig.get_config_var("Py_GIL_DISABLED")) or None}
    info["hostname"] = platform.node()
    order = ["hostname", "system", "os", "architecture", "cpu", "memory", "gpus", "npus", "storage", "power",
             "python", "error"]
    return _clean({k: info[k] for k in order if k in info})


def summary_lines(info):
    """Short human-readable description, one line per component."""
    lines = []
    s, o, a, c, m = (info.get(k, {}) for k in ("system", "os", "architecture", "cpu", "memory"))
    if s:
        lines.append(f"System:  {' '.join(v for v in (s.get('manufacturer'), s.get('model')) if v)}")
    os_ver = " ".join(str(v) for v in (o.get("name"), o.get("version")) if v)
    lines.append(f"OS:      {os_ver}" + (f" (build {o['build']})" if o.get("build") else "")
                 + (f", kernel {o['kernel']}" if o.get("kernel") and not o.get("build") else ""))
    emu = {True: " (emulated)", "partly": " (x64 extension modules emulated)"}.get(a.get("emulated"), "")
    lines.append(f"Arch:    {a.get('machine')}, Python process {a.get('python_process')}{emu}")
    cores = f"{c.get('physical_cores', '?')} cores / {c.get('logical_cpus', '?')} threads"
    if c.get("core_classes"):
        cores += " (" + " + ".join(f"{k['cores']} {k['kind']}" for k in c["core_classes"]) + ")"
    freq = f", {c['max_mhz'] / 1000:.2f} GHz" if c.get("max_mhz") else ""
    lines.append(f"CPU:     {c.get('name')}, {cores}{freq}")
    if c.get("features"):
        lines.append(f"         ISA: {' '.join(c['features'])}")
    mem = f"{m.get('total_gb')} GB" + "".join(f" {m[k]}" for k in ("type",) if m.get(k)) \
        + (f"-{m['speed_mts']}" if m.get("speed_mts") else "")
    lines.append(f"RAM:     {mem}")
    for g in info.get("gpus", []):
        if g.get("virtual"):
            continue
        extra = [f"{g['dedicated_memory_gb']} GB dedicated" if g.get("dedicated_memory_gb") else None,
                 f"{g['gpu_cores']} cores" if g.get("gpu_cores") else None,
                 f"driver {g.get('nvidia_driver') or g.get('driver')}" if g.get("nvidia_driver") or g.get("driver") else None]
        lines.append(f"GPU:     {g.get('name')}" + "".join(f", {e}" for e in extra if e))
    for n in info.get("npus", []) or [{"name": "none found"}]:
        lines.append(f"NPU:     {n.get('name')}" + (f", driver {n['driver']}" if n.get("driver") else ""))
    for d in info.get("storage", []):
        if d.get("system_disk"):
            lines.append(f"Disk:    {d.get('name')}, {d.get('media')} {d.get('bus')}, {d.get('size_gb'):.0f} GB")
    p = info.get("power", {})
    if p:
        lines.append("Power:   " + ", ".join(str(p[k]) for k in ("source", "plan", "mode", "governor") if p.get(k)))
    py = info.get("python", {})
    lines.append(f"Python:  {py.get('implementation')} {py.get('version')} ({py.get('platform')})")
    return lines


def summary_line(info=None):
    """One-line description for a report title or a table cell."""
    info = info or system_info()
    c, m, a = info.get("cpu", {}), info.get("memory", {}), info.get("architecture", {})
    parts = [" ".join(v for v in (info.get("system", {}).get("manufacturer"), info.get("system", {}).get("model")) if v),
             f"{info['os'].get('name')} {info['os'].get('version') or ''}".strip() + f" {a.get('machine')}",
             f"{c.get('name')} ({c.get('physical_cores', '?')}C/{c.get('logical_cpus', '?')}T)",
             f"{m.get('total_gb')} GB RAM"]
    parts += [g["name"] for g in info.get("gpus", []) if not g.get("virtual")]
    parts += [n["name"] for n in info.get("npus", [])]
    return " | ".join(p for p in parts if p)


_NOISE_WORDS = {"intel", "amd", "qualcomm", "nvidia", "geforce", "apple", "microsoft", "processor", "cpu", "gpu",
                "graphics", "core", "corporation", "incorporated", "technologies", "inc", "device", "adapter"}
_NPU_NAMES = [(r"hexagon", "hexagon"), (r"ai boost|intel.*npu", "intel-ai-boost"),
              (r"amd|xdna|ipu|npu compute accelerator", "amd-xdna"), (r"neural engine", "apple-ane")]


def _short_name(name):
    """'Snapdragon(R) X 12-core X1E80100 @ 3.40 GHz' -> 'snapdragon-x1e80100', 'NVIDIA GeForce RTX 4090' -> 'rtx-4090'."""
    s = re.sub(r"\((?:R|TM|C)\)|[®™]", "", name or "", flags=re.I)
    s = re.sub(r"\s(?:@|w/|with)\s.*$", "", s, flags=re.I)  # clock speed, "with Radeon Graphics"
    s = re.sub(r"\([^)]*\)|\b\d+-core\b|\b\d+(?:st|nd|rd|th) gen\b", " ", s, flags=re.I)
    words = [w for w in re.split(r"[^a-z0-9+]+", s.lower()) if w and w not in _NOISE_WORDS
             and not (len(w) == 1 and w.isalpha())]
    return re.sub(r"-?\+-?", "+", "-".join(words)).strip("+-")


def short_id(info=None):
    """Compact, file-name safe description of the computer, for example
    'win_arm64_cpu_snapdragon-x1e80100_12x3.42GHz_ram_32GB_gpu_adreno-x1-85_npu_hexagon'.
    Fields that are unknown (or absent, such as an NPU) are left out; several GPUs/NPUs are joined with '+'."""
    info = info or system_info()
    os_name = info.get("os", {}).get("name", "").lower()
    parts = [next((v for k, v in (("windows", "win"), ("macos", "mac")) if k in os_name),
                  "linux" if info.get("os", {}).get("kernel") else (os_name.split() or ["unknown"])[0]),
             info.get("architecture", {}).get("machine") or "unknown"]
    c = info.get("cpu", {})
    parts += ["cpu", _short_name(c.get("name")) or "unknown"]
    cores = c.get("physical_cores") or c.get("logical_cpus")
    if cores:
        parts.append(f"{cores}x{c['max_mhz'] / 1000:.2f}GHz" if c.get("max_mhz") else f"{cores}c")
    if info.get("memory", {}).get("total_gb"):
        parts += ["ram", f"{round(info['memory']['total_gb'])}GB"]
    gpus = list(dict.fromkeys(_short_name(g.get("name")) for g in info.get("gpus", []) if not g.get("virtual")))
    if any(gpus):
        parts += ["gpu", "+".join(g for g in gpus if g)]
    npus = []
    for n in info.get("npus", []):
        name = n.get("name") or ""
        npus.append(next((v for pat, v in _NPU_NAMES if re.search(pat, name, re.I)), _short_name(name)))
    if any(npus):
        parts += ["npu", "+".join(dict.fromkeys(n for n in npus if n))]
    return "_".join(parts)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="print all details as JSON")
    ap.add_argument("--short", action="store_true", help="print only a compact id, e.g. win_arm64_cpu_..._npu_...")
    ap.add_argument("-o", "--output", help="also write the JSON to this file")
    args = ap.parse_args(argv)
    info = system_info()
    if args.short:
        print(short_id(info))
        return
    if args.output:
        Path(args.output).write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.json:
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(info, indent=2, ensure_ascii=False))
    else:
        print("\n".join(summary_lines(info)))


if __name__ == "__main__":
    main()
