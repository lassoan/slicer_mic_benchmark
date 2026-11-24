"""Select and download the benchmark test data: 20 abdominal CT series from NCI Imaging Data Commons.

By default, downloads the series listed in manifest/idc_series.csv (the same data on every computer).
--reselect runs the selection again and rewrites the manifest: selection is deterministic (sorted by
SeriesInstanceUID after filtering), so it selects the same series as long as the IDC index version (recorded in the
manifest) is the same.

Usage: python download_idc.py [--reselect] [--select-only]
"""

import argparse
import csv
from pathlib import Path

from idc_index import IDCClient

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest" / "idc_series.csv"
DICOM_DIR = ROOT / "data" / "dicom"

# collection -> number of series. Half from a curated research collection, half from clinical collections
# (more variation in scanners, reconstruction and geometry).
QUOTA = {
    "pancreas_ct": 10,
    "c4kc_kits": 2,
    "tcga_kirc": 2,
    "tcga_lihc": 2,
    "cptac_pda": 2,
    "hcc_tace_seg": 2,
}

# Series used for the (slow) AI segmentation section: the first 5 rows of the manifest that are marked here
AI_SUBSET_SIZE = 5

QUERY = """
SELECT collection_id, PatientID, StudyInstanceUID, SeriesInstanceUID, SeriesDescription, BodyPartExamined,
       Manufacturer, ManufacturerModelName, transfer_syntax_name, instanceCount, series_size_MB,
       license_short_name, source_DOI
FROM index
WHERE Modality = 'CT'
  AND collection_id IN ({collections})
  AND SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'  -- CT Image Storage (single-frame)
  AND PhotometricInterpretation = 'MONOCHROME2'
  AND instanceCount BETWEEN 100 AND 700
  AND series_size_MB < 400
  AND NOT regexp_matches(lower(coalesce(SeriesDescription, '')), 'scout|topo|loc|survey|dose|report|screen|mip|cor|sag')
ORDER BY collection_id, SeriesInstanceUID
"""


def select(client):
    collections = ", ".join(f"'{c}'" for c in QUOTA)
    df = client.sql_query(QUERY.format(collections=collections))
    rows = []
    for collection, quota in QUOTA.items():
        used_patients = set()
        for r in df[df.collection_id == collection].itertuples(index=False):
            if r.PatientID in used_patients:
                continue  # one series per patient
            used_patients.add(r.PatientID)
            rows.append(r._asdict())
            if len(used_patients) == quota:
                break
        if len(used_patients) < quota:
            raise RuntimeError(f"Only {len(used_patients)} series found in {collection}, need {quota}")
    # Interleave collections for the AI subset: first 5 rows = 3 pancreas_ct + 2 clinical
    for i, r in enumerate(rows):
        r["case_id"] = f"case{i + 1:02d}"
    ai_ids = {"case01", "case02", "case03", "case11", "case13"}
    for r in rows:
        r["ai_subset"] = int(r["case_id"] in ai_ids)
        r["idc_version"] = client.get_idc_version()
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reselect", action="store_true", help="select the series again and rewrite the manifest")
    parser.add_argument("--select-only", action="store_true", help="with --reselect: do not download")
    args = parser.parse_args()

    client = IDCClient()
    if MANIFEST.exists() and not args.reselect:
        with MANIFEST.open() as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            r["instanceCount"] = int(r["instanceCount"])
        download(client, rows)
        return
    rows = select(client)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    fields = ["case_id", "ai_subset"] + [k for k in rows[0] if k not in ("case_id", "ai_subset")]
    with MANIFEST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    total_mb = sum(r["series_size_MB"] for r in rows)
    print(f"Selected {len(rows)} series, {total_mb:.0f} MB -> {MANIFEST}")
    for r in rows:
        print(f"  {r['case_id']} {r['collection_id']:14s} {r['instanceCount']:4d} slices "
              f"{r['series_size_MB']:6.1f} MB  {r['SeriesDescription']}")

    # Citation / attribution required by the CC BY licenses
    dois = sorted({(r["collection_id"], r["source_DOI"], r["license_short_name"]) for r in rows})
    with (MANIFEST.parent / "ATTRIBUTION.md").open("w") as f:
        f.write("# Test data attribution\n\nImages were obtained from the NCI Imaging Data Commons "
                f"({rows[0]['idc_version']}, https://imaging.datacommons.cancer.gov/). "
                "Original collections, data DOIs and licenses:\n\n| Collection | DOI | License |\n| --- | --- | --- |\n")
        for c, doi, lic in dois:
            f.write(f"| {c} | https://doi.org/{doi} | {lic} |\n")

    if not args.select_only:
        download(client, rows)


def download(client, rows):
    DICOM_DIR.mkdir(parents=True, exist_ok=True)
    for r in rows:
        out = DICOM_DIR / r["case_id"]
        if out.exists() and len(list(out.glob("*.dcm"))) == r["instanceCount"]:
            continue
        out.mkdir(exist_ok=True)
        client.download_from_selection(seriesInstanceUID=[r["SeriesInstanceUID"]], downloadDir=str(out),
                                       dirTemplate="", show_progress_bar=False, quiet=True)
        print(f"Downloaded {r['case_id']}: {len(list(out.glob('*.dcm')))} files")


if __name__ == "__main__":
    main()
