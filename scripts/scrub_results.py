"""Remove personal information from existing result folders (results written before bench/privacy.py existed).

For each result JSON: stores the CPU load of other processes from the local load.log as numbers
("foreign_load"), then applies bench/privacy.py (paths relative to <repo>, <python>, <home>, ...; no host or user
names). Run on the computer that produced the results, so that its paths and names are known.

Usage: python scripts/scrub_results.py <results folder> [...]
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import benchmark  # noqa: E402
from bench.privacy import Scrubber  # noqa: E402


def interpreter_roots():
    """Base interpreters of the environments in .envs/ (pyvenv.cfg "home"), mapped to <python>."""
    roots = {}
    for cfg in (ROOT / ".envs").glob("*/pyvenv.cfg"):
        for line in cfg.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "home":
                home = Path(value.strip())
                roots[str(home.parent if home.name.lower() == "bin" else home)] = "<python>"
    return roots


def main():
    scrub = Scrubber(interpreter_roots())
    for folder in sys.argv[1:]:
        results = Path(folder).resolve()
        benchmark.annotate_load(results)
        n = 0
        for f in sorted(results.rglob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            clean = scrub(d)
            if clean != d:
                f.write_text(json.dumps(clean, indent=1), encoding="utf-8")
                n += 1
        print(f"{results.name}: {n} files changed")


if __name__ == "__main__":
    main()
