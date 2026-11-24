"""Section 1: file I/O and DICOM geometry checks, over all 20 CT series.

1a read DICOM headers (SimpleITK/GDCM, one file at a time)
1b geometry checks in pure Python (group by series, orientation, spacing, gaps, tilt)
1c read DICOM volumes (SimpleITK ImageSeriesReader)
1d write NRRD (pynrrd, raw and gzip)      1e write NIfTI (nibabel, .nii and .nii.gz)
1f read NRRD and NIfTI back (pynrrd, nibabel) and compare with the DICOM volume
"""

import math
import shutil
from pathlib import Path

import nibabel as nib
import nrrd
import pydicom
import numpy as np
import SimpleITK as sitk

from bench import config, harness

DEFAULT_REPEATS = 3

TAGS = {
    "series": "0020|000e",
    "ipp": "0020|0032",
    "iop": "0020|0037",
    "pixel_spacing": "0028|0030",
    "thickness": "0018|0050",
    "rows": "0028|0010",
    "cols": "0028|0011",
}


def read_headers(cases):
    """1a: read header of every DICOM file. Returns {case: [ {file, tag values...} ]}."""
    headers = {}
    reader = sitk.ImageFileReader()
    reader.LoadPrivateTagsOff()
    for case in cases:
        items = []
        for f in sorted((config.DICOM_DIR / case).glob("*.dcm")):
            reader.SetFileName(str(f))
            reader.ReadImageInformation()
            item = {"file": str(f)}
            for key, tag in TAGS.items():
                item[key] = reader.GetMetaData(tag) if reader.HasMetaDataKey(tag) else ""
            items.append(item)
        headers[case] = items
    return headers


def read_headers_pydicom(cases):
    """1a (pure Python): parse the header of every DICOM file with pydicom, as a DICOM browser does."""
    count = 0
    uids = set()
    for case in cases:
        for f in sorted((config.DICOM_DIR / case).glob("*.dcm")):
            ds = pydicom.dcmread(f, stop_before_pixels=True)
            uids.add(ds.SeriesInstanceUID)
            _ = (ds.ImagePositionPatient, ds.ImageOrientationPatient, ds.PixelSpacing, ds.get("SliceThickness"),
                 ds.PatientID, ds.StudyInstanceUID, ds.Modality, ds.get("SeriesDescription"))
            count += 1
    return {"files": count, "series": len(uids)}


GEOMETRY_INNER_REPEATS = 50  # the check takes ~20 ms per pass over all series; repeat for a measurable time


def _floats(s):
    return [float(x) for x in s.replace(" ", "").split("\\") if x]


def check_geometry(headers):
    """1b: pure-Python geometry checks. Returns {case: {series_uid: report}} and sorted file lists."""
    reports = {}
    sorted_files = {}
    for case, items in headers.items():
        by_series = {}
        for it in items:
            by_series.setdefault(it["series"].strip(), []).append(it)
        case_report = {}
        for uid, sl in by_series.items():
            iops = [_floats(it["iop"]) for it in sl]
            ref = iops[0]
            parallel = all(max(abs(a - b) for a, b in zip(ref, iop)) <= config.GEOMETRY_ORIENTATION_TOL for iop in iops)
            row, col = ref[:3], ref[3:]
            normal = [row[1] * col[2] - row[2] * col[1],
                      row[2] * col[0] - row[0] * col[2],
                      row[0] * col[1] - row[1] * col[0]]
            positioned = []
            for it in sl:
                p = _floats(it["ipp"])
                positioned.append((p[0] * normal[0] + p[1] * normal[1] + p[2] * normal[2], p, it["file"]))
            positioned.sort(key=lambda x: x[0])
            dists = [b[0] - a[0] for a, b in zip(positioned, positioned[1:])]
            sd = sorted(dists)
            median = sd[len(sd) // 2] if sd else 0.0
            max_dev = max((abs(d - median) for d in dists), default=0.0)
            duplicates = sum(1 for d in dists if abs(d) < 1e-3)
            gaps = sum(1 for d in dists if d > 1.5 * median)
            # Angle between the slice stacking direction and the slice normal (gantry tilt or shear)
            first, last = positioned[0][1], positioned[-1][1]
            stack = [b - a for a, b in zip(first, last)]
            stack_len = math.sqrt(sum(x * x for x in stack))
            tilt = 0.0
            if stack_len > 0:
                c = abs(sum(s * n for s, n in zip(stack, normal))) / stack_len
                tilt = math.degrees(math.acos(min(1.0, c)))
            uniform = median > 0 and max_dev <= config.GEOMETRY_SPACING_REL_TOL * median
            case_report[uid] = {
                "slices": len(sl),
                "parallel": parallel,
                "uniform_spacing": uniform,
                "slice_spacing": round(median, 4),
                "max_spacing_deviation": round(max_dev, 4),
                "duplicates": duplicates,
                "gaps": gaps,
                "tilt_deg": round(tilt, 3),
                "pixel_spacing": _floats(sl[0]["pixel_spacing"]),
                "thickness": sl[0]["thickness"].strip(),
                "matrix": [int(sl[0]["rows"]), int(sl[0]["cols"])],
            }
            if len(by_series) == 1:
                sorted_files[case] = [x[2] for x in positioned]
        reports[case] = case_report
    return reports, sorted_files


def read_volumes(sorted_files):
    """1c: read each series as a volume with SimpleITK."""
    volumes = {}
    for case, files in sorted_files.items():
        reader = sitk.ImageSeriesReader()
        reader.SetFileNames(files)
        img = reader.Execute()
        volumes[case] = {
            "array": sitk.GetArrayFromImage(img),  # (z, y, x)
            "spacing": img.GetSpacing(),
            "origin": img.GetOrigin(),
            "direction": img.GetDirection(),
        }
    return volumes


def _lps_axes(v):
    d = np.array(v["direction"]).reshape(3, 3)
    return d * np.array(v["spacing"])  # column i = direction of axis i scaled by spacing


def write_nrrd(volumes, out_dir, encoding):
    sizes = 0
    for case, v in volumes.items():
        axes = _lps_axes(v)
        header = {
            "space": "left-posterior-superior",
            "space directions": axes.T,  # one row per axis
            "space origin": np.array(v["origin"]),
            "kinds": ["domain", "domain", "domain"],
            "encoding": encoding,
        }
        f = out_dir / f"{case}-{encoding}.nrrd"
        nrrd.write(str(f), v["array"].T, header, compression_level=config.NRRD_GZIP_LEVEL)
        sizes += f.stat().st_size
    return sizes


def write_nifti(volumes, out_dir, ext):
    nib.openers.Opener.default_compresslevel = config.NIFTI_GZIP_LEVEL
    sizes = 0
    for case, v in volumes.items():
        affine = np.eye(4)
        affine[:3, :3] = _lps_axes(v)
        affine[:3, 3] = v["origin"]
        affine = np.diag([-1, -1, 1, 1]) @ affine  # LPS -> RAS
        img = nib.Nifti1Image(v["array"].T, affine)
        img.set_data_dtype(np.int16)
        f = out_dir / f"{case}{ext}"
        nib.save(img, str(f))
        sizes += f.stat().st_size
    return sizes


def read_nrrd(cases, out_dir, encoding):
    total = 0
    for case in cases:
        data, header = nrrd.read(str(out_dir / f"{case}-{encoding}.nrrd"))
        total += int(data.sum(dtype=np.int64))
    return total


def read_nifti(cases, out_dir, ext, as_float):
    total = 0
    for case in cases:
        img = nib.load(str(out_dir / f"{case}{ext}"))
        data = img.get_fdata(dtype=np.float32) if as_float else np.asarray(img.dataobj)
        total += int(data.sum(dtype=np.float64)) if as_float else int(data.sum(dtype=np.int64))
    return total


def run(runner, cases=None, tasks=None, threads=1, env="unknown"):
    cases = cases or config.all_cases()
    harness.set_library_threads(threads)
    out_dir = config.WORK_DIR / env / "io"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    def want(name):
        return tasks is None or any(name.startswith(t) for t in tasks)

    state = {}

    def t_headers():
        state["headers"] = read_headers(cases)
        return {"files": sum(len(v) for v in state["headers"].values())}
    runner.run("1a_read_dicom_headers_sitk", t_headers)
    runner.run("1a_read_dicom_headers_pydicom", lambda: read_headers_pydicom(cases))

    def t_geometry():
        for _ in range(GEOMETRY_INNER_REPEATS):
            state["report"], state["sorted"] = check_geometry(state["headers"])
        return state["report"]
    runner.run(f"1b_check_geometry_pure_python_x{GEOMETRY_INNER_REPEATS}", t_geometry)

    def t_read():
        state["volumes"] = read_volumes(state["sorted"])
        return {c: int(v["array"].sum(dtype=np.int64)) for c, v in state["volumes"].items()}
    ref_sums = runner.run("1c_read_dicom_volumes_sitk", t_read)
    vol_total = sum(ref_sums.values())
    vols = state["volumes"]
    n_cases = list(vols)

    if want("1d"):
        runner.run("1d_write_nrrd_raw", lambda: {"bytes": write_nrrd(vols, out_dir, "raw")})
        runner.run("1d_write_nrrd_gzip", lambda: {"bytes": write_nrrd(vols, out_dir, "gzip")})
    if want("1e"):
        runner.run("1e_write_nifti", lambda: {"bytes": write_nifti(vols, out_dir, ".nii")})
        runner.run("1e_write_nifti_gz", lambda: {"bytes": write_nifti(vols, out_dir, ".nii.gz")})
    if want("1f"):
        runner.run("1f_read_nrrd_raw", lambda: {"sum": read_nrrd(n_cases, out_dir, "raw"), "expected": vol_total})
        runner.run("1f_read_nrrd_gzip", lambda: {"sum": read_nrrd(n_cases, out_dir, "gzip"), "expected": vol_total})
        runner.run("1f_read_nifti_raw_dataobj", lambda: {"sum": read_nifti(n_cases, out_dir, ".nii", False), "expected": vol_total})
        runner.run("1f_read_nifti_gz_dataobj", lambda: {"sum": read_nifti(n_cases, out_dir, ".nii.gz", False), "expected": vol_total})
        runner.run("1f_read_nifti_gz_fdata_float32", lambda: {"sum": read_nifti(n_cases, out_dir, ".nii.gz", True), "expected": vol_total})

    shutil.rmtree(out_dir, ignore_errors=True)
    return {"geometry_report": state["report"], "cases": cases}
