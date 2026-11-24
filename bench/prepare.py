"""Prepare inputs for sections 2-5 (not timed): convert each DICOM series to data/nrrd/<case>.nrrd (raw) and
data/nifti/<case>.nii.gz, and write the geometry report to manifest/geometry.json.

Usage: python -m bench.prepare
"""

import json

import nibabel as nib
import numpy as np

from bench import config
from bench.t1_io import check_geometry, read_headers, read_volumes, write_nifti, write_nrrd


def main():
    cases = config.all_cases()
    headers = read_headers(cases)
    report, sorted_files = check_geometry(headers)
    (config.ROOT / "manifest" / "geometry.json").write_text(json.dumps(report, indent=1))
    config.NRRD_DIR.mkdir(parents=True, exist_ok=True)
    config.NIFTI_DIR.mkdir(parents=True, exist_ok=True)
    for case in cases:
        if case not in sorted_files:
            print(f"{case}: more than one series, skipped")
            continue
        vols = read_volumes({case: sorted_files[case]})
        write_nrrd(vols, config.NRRD_DIR, "raw")
        (config.NRRD_DIR / f"{case}-raw.nrrd").replace(config.NRRD_DIR / f"{case}.nrrd")
        write_nifti(vols, config.NIFTI_DIR, ".nii.gz")
        v = vols[case]
        print(f"{case}: {v['array'].shape[::-1]} spacing {np.round(v['spacing'], 3)}  "
              f"{json.dumps(list(report[case].values())[0])}")


if __name__ == "__main__":
    main()
