#!/usr/bin/env python3
"""
compare_typecheckers.py  –  v2 (whitespace-tolerant)

Run Pyright & Pyrefly, compare diagnostics, report:
  • overlapping files
  • overlapping file+row pairs
  • errors only in Pyright
  • errors only in Pyrefly

Usage:
    python compare_typecheckers.py            # whole project
    python compare_typecheckers.py file.py    # single file
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from typing import List, Set, Tuple

# ───────── Regexes ─────────
# Optional leading whitespace (^\s*) is the only change.

PYRIGHT_RE = re.compile(
    r"""
    ^\s*                                   # ← NEW: swallow leading spaces
    (?P<path>[^:]+):
    (?P<row>\d+):
    (?P<col>\d+)
    \s+-\s+error:\s+
    (?P<msg>.+?)
    \s+\([^)]+\)$
""",
    re.VERBOSE,
)

PYREFLY_RE = re.compile(
    r"""
    ^\s*                                   # ← NEW: swallow leading spaces
    ERROR\s+
    (?P<path>[^:]+):
    (?P<row>\d+):
    (?P<col>\d+)
    (?:-\d+)?:\s+
    (?P<msg>.+?)\s+
    \[[^]]+\]$
""",
    re.VERBOSE,
)

# ───── helpers ─────
def run(cmd: List[str], label: str) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        sys.exit(f"❌ {label} not found: {exc.filename!r}")
    if proc.returncode:
        print(f"⚠️  {label} exited {proc.returncode} (likely just means it found errors).")
    return proc.stdout + proc.stderr


def parse(text: str, pattern: re.Pattern[str]) -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    for line in text.splitlines():
        m = pattern.match(line)
        if m:
            # strip any leading/trailing blanks around path, just in case
            out.append((m["path"].strip(), m["row"], m["msg"].strip()))
    return out


# ───── main ─────
def main() -> None:
    p = argparse.ArgumentParser(description="Compare Pyright vs Pyrefly diagnostics")
    p.add_argument("targets", nargs="*", help="Files / dirs to check")
    args = p.parse_args()

    pyright_cmd = ["pyright", *args.targets]
    pyrefly_cmd = ["pyrefly", "check", "--output-format=min-text", *args.targets]

    print(f"▶ Pyright: {' '.join(pyright_cmd)}")
    pyright_raw = run(pyright_cmd, "pyright")

    print(f"▶ Pyrefly: {' '.join(pyrefly_cmd)}")
    pyrefly_raw = run(pyrefly_cmd, "pyrefly")

    py_errs = parse(pyright_raw, PYRIGHT_RE)
    pr_errs = parse(pyrefly_raw, PYREFLY_RE)

    # normalised keys
    py_key = {f"{p}:{row}:{msg}" for p, row, msg in py_errs}
    pr_key = {f"{p}:{row}:{msg}" for p, row, msg in pr_errs}

    overlapping_files: Set[str] = {p for p, _, _ in py_errs} & {p for p, _, _ in pr_errs}
    overlapping_locs: Set[str] = {f"{p}:{row}" for p, row, _ in py_errs} & {
        f"{p}:{row}" for p, row, _ in pr_errs
    }
    py_only = py_key - pr_key
    pr_only = pr_key - py_key

    # ─── report ───
    print("\n================ SUMMARY ================")
    print(f"Overlapping files               : {len(overlapping_files)}")
    print(f"Overlapping file & row pairs    : {len(overlapping_locs)}")
    print(f"Errors only in Pyright          : {len(py_only)}")
    print(f"Errors only in Pyrefly          : {len(pr_only)}")
    print("=========================================\n")

    if py_only:
        print("▶ Pyright-only errors:")
        for e in sorted(py_only):
            print("  ", e)
        print()
    if pr_only:
        print("▶ Pyrefly-only errors:")
        for e in sorted(pr_only):
            print("  ", e)
        print()


if __name__ == "__main__":
    main()
