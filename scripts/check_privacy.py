"""Check that files to be published contain no personal information: absolute paths, user profile folders, and
(when run on the computer that produced the results) its computer name and user name. Exit code 1 if anything is
found. Used before committing results and in the GitHub workflow.

Usage: python scripts/check_privacy.py [files or folders; default: results]
"""

import json
import os
import platform
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".json", ".md", ".csv", ".txt", ".html"}
PATTERNS = [
    (r"(?<![A-Za-z0-9])[A-Za-z]:[\\/](?=[A-Za-z0-9_.$ -]+[\\/])", "absolute path"),
    (r"(?i)[\\/](Users|home|Documents and Settings)[\\/](?!<user>)[A-Za-z0-9._-]+", "user profile path"),
    (r"\\\\[A-Za-z0-9._-]+\\[A-Za-z0-9$._-]+", "network path"),
]


def local_names():
    names = {platform.node(), os.environ.get("COMPUTERNAME", ""), os.environ.get("USERNAME", ""), Path.home().name}
    return [n for n in names if n and len(n) >= 3]


def strings(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)
    elif isinstance(obj, str):
        yield obj


def check_file(f, patterns):
    text = f.read_text(encoding="utf-8", errors="replace")
    try:
        items = list(strings(json.loads(text))) if f.suffix == ".json" else text.splitlines()
    except ValueError:
        items = text.splitlines()
    found = []
    for s in items:
        for rx, what in patterns:
            m = rx.search(s)
            if m:
                found.append(f"{what}: ...{s[max(0, m.start() - 40):m.end() + 40]}...")
    return found


def main():
    targets = [Path(a) for a in sys.argv[1:]] or [ROOT / "results"]
    patterns = [(re.compile(p), w) for p, w in PATTERNS]
    patterns += [(re.compile(r"(?i)(?<![A-Za-z0-9])" + re.escape(n) + r"(?![A-Za-z0-9])"), "computer/user name")
                 for n in local_names()]
    files = []
    for t in targets:
        files += [t] if t.is_file() else [f for f in t.rglob("*") if f.suffix in TEXT_SUFFIXES]
    bad = 0
    for f in sorted(files):
        found = check_file(f, patterns)
        if found:
            bad += 1
            print(f"{f}:")
            for line in sorted(set(found))[:5]:
                print(f"  {line}")
    print(f"checked {len(files)} files: {bad} with personal information")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
