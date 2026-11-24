"""Download AI model weights once (not timed) into data/models/.

- TotalSegmentator: task "total" fast (3 mm) and full resolution weights, into data/models/totalseg
  (TOTALSEG_HOME_DIR). Usage statistics reporting is turned off in its config.
- MONAIAuto3DSeg: "Abdominal organs TS2 - quick" (3 mm) and "Abdominal organs TS2" models, from the
  SlicerMONAIAuto3DSeg GitHub releases, into data/models/monai/<name>/model.pt

Usage: python scripts/download_models.py
"""

import os
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bench.t5_ai import MONAI_MODELS, MONAI_DIR, TOTALSEG_HOME, setup_totalseg_env  # noqa: E402


def download_monai():
    for name, url in MONAI_MODELS.items():
        out = MONAI_DIR / name
        if (out / "model.pt").exists():
            continue
        out.mkdir(parents=True, exist_ok=True)
        zip_path = MONAI_DIR / f"{name}.zip"
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(out)
        zip_path.unlink()
        found = list(out.rglob("model.pt"))
        print(f"  {name}: {found}")


def download_totalseg():
    setup_totalseg_env()
    from totalsegmentator.config import setup_totalseg, set_config_key
    from totalsegmentator.libs import download_pretrained_weights
    setup_totalseg()
    set_config_key("send_usage_stats", False)
    for task_id in [297, 291, 292, 293, 294, 295]:  # 297 = total 3 mm (fast), 291-295 = total full resolution
        download_pretrained_weights(task_id)
    print(f"TotalSegmentator weights in {TOTALSEG_HOME}")


if __name__ == "__main__":
    download_monai()
    download_totalseg()
