"""Remove personal information from benchmark results before they are written (results are published).

- Absolute paths become relative to a known root: <repo> (this repository), <python> (the base interpreter of an
  environment), <home> (the user profile), <windows>, <programfiles>, <programdata>; any other absolute path is
  reduced to <path>/<file name>. Paths in the user profile never keep the user name.
- Keys that identify the computer or the user (hostname, user name) are dropped; the computer name and user name
  are also replaced wherever they appear in a string.
- Process names of other programs are not recorded at all (load is stored as numbers only).

    from bench.privacy import scrub
    clean = scrub(data)                       # roots of the current process
    clean = scrub(data, extra_roots={...})    # offline: also map these {path: tag} roots
"""

import os
import platform
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DROP_KEYS = {"hostname", "host", "computer_name", "node", "user", "username", "user_name"}
_ABS = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\)")
_USER_DIR = re.compile(r"(?i)([A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/])[^\\/]+")


def default_roots():
    env = os.environ
    roots = {str(ROOT): "<repo>", sys.base_prefix: "<python>", str(Path.home()): "<home>"}
    for var, tag in (("WINDIR", "<windows>"), ("ProgramFiles", "<programfiles>"),
                     ("ProgramFiles(x86)", "<programfiles>"), ("ProgramData", "<programdata>")):
        if env.get(var):
            roots[env[var]] = tag
    return roots


def _norm(p):
    return p.replace("/", "\\").rstrip("\\").lower()


class Scrubber:
    def __init__(self, extra_roots=None):
        roots = default_roots()
        roots.update(extra_roots or {})
        # longest first, so <repo>\.envs\x64 is not taken as <python> when the interpreter lives in the repository
        self.roots = sorted(((_norm(k), v) for k, v in roots.items() if k), key=lambda kv: -len(kv[0]))
        names = {platform.node(), os.environ.get("COMPUTERNAME", ""), os.environ.get("USERNAME", ""),
                 Path.home().name}
        self.names = [n for n in names if n and len(n) >= 3]

    def path(self, s):
        n = s.replace("/", "\\")
        low = n.lower()
        for prefix, tag in self.roots:
            if low == prefix or low.startswith(prefix + "\\"):
                return tag + n[len(prefix):].replace("\\", "/")
        return "<path>/" + n.rstrip("\\").split("\\")[-1]

    def text(self, s):
        if _ABS.match(s):
            s = self.path(s)
        s = _USER_DIR.sub(r"\1<user>", s)
        for name in self.names:
            s = re.sub(r"(?i)(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", "<computer>", s)
        return s

    def __call__(self, obj):
        if isinstance(obj, dict):
            return {self.text(k) if isinstance(k, str) else k: self(v) for k, v in obj.items()
                    if not (isinstance(k, str) and k.lower() in DROP_KEYS)}
        if isinstance(obj, (list, tuple)):
            return [self(v) for v in obj]
        if isinstance(obj, str):
            return self.text(obj)
        return obj


def scrub(obj, extra_roots=None):
    return Scrubber(extra_roots)(obj)
