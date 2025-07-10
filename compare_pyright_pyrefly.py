#!/usr/bin/env python3
"""
compare_typecheckers.py  –  tolerant, with summary + mismatch list

• Counts:
    - overlapping files
    - overlapping file+row pairs
    - errors only in Pyright (msg-sensitive)
    - errors only in Pyrefly  (msg-sensitive)
• Lists:
    - Pyright-only locations (file:row) with their messages
    - Pyrefly-only locations with their messages

Run over the whole project:
    python compare_typecheckers.py

Or pass paths to narrow the check:
    python compare_typecheckers.py path/to/file.py other_dir/
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple

# ───────── unified regex (handles leading spaces, optional 'ERROR') ───────── #
DIAG_RE = re.compile(
    r"""^\s*(?:ERROR\s+)?(?P<path>[^:]+):(?P<row>\d+):(?P<rest>.*)""",
    re.VERBOSE,
)

# ───────── helpers ───────── #
def run(cmd: List[str], label: str) -> str:
    """Run command and return stdout+stderr (don’t abort on non-zero exit)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as e:
        sys.exit(f"❌ {label} not found: {e.filename!r}")
    return p.stdout + p.stderr


def parse(text: str) -> List[Tuple[str, str, str]]:
    """Return list of (path, row, rest_of_line)."""
    out: List[Tuple[str, str, str]] = []
    for line in text.splitlines():
        m = DIAG_RE.match(line)
        if m:
            out.append((m["path"].strip(), m["row"], m["rest"].strip()))
    return out


# ───────── main ───────── #
def main() -> None:
    ap = argparse.ArgumentParser(description="Compare Pyright vs Pyrefly output")
    ap = argparse.ArgumentParser(
        description="Compare Pyright vs Pyrefly output",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument(
        "-a",
        "--agree-only",
        action="store_true",
        help=(
            "Only list rows where *both* tools report an error. "
            "For each agreed row the messages from Pyright and Pyrefly "
            "are shown."
        ),
    )
    ap.add_argument("targets", nargs="*", help="files / directories to check")
    args = ap.parse_args()

    py_cmd = ["pyright", *args.targets]
    pr_cmd = ["pyrefly", "check", "--output-format=min-text", *args.targets]

    print("▶ Pyright:", " ".join(py_cmd))
    py_raw = run(py_cmd, "pyright")

    print("▶ Pyrefly:", " ".join(pr_cmd))
    pr_raw = run(pr_cmd, "pyrefly")

    py_list = parse(py_raw)
    pr_list = parse(pr_raw)

    # --- message-sensitive sets (path:row:msg) for “errors only” counts
    py_full = {f"{p}:{row}:{rest}" for p, row, rest in py_list}
    pr_full = {f"{p}:{row}:{rest}" for p, row, rest in pr_list}

    # --- message-insensitive keys (path:row) for overlap / mismatch logic
    py_rows = {f"{p}:{row}" for p, row, _ in py_list}
    pr_rows = {f"{p}:{row}" for p, row, _ in pr_list}

    overlapping_files: Set[str] = {p for p, _, _ in py_list} & {p for p, _, _ in pr_list}
    overlapping_locs: Set[str] = py_rows & pr_rows

    py_only_full = py_full - pr_full
    pr_only_full = pr_full - py_full

    # --- build maps path:row -> {messages} for printing
    def to_map(items: List[Tuple[str, str, str]]) -> Dict[str, Set[str]]:
        mp: Dict[str, Set[str]] = defaultdict(set)
        for p, row, rest in items:
            mp[f"{p}:{row}"].add(rest)
        return mp

    py_map = to_map(py_list)
    pr_map = to_map(pr_list)

    py_only_rows = py_rows - pr_rows
    pr_only_rows = pr_rows - py_rows

    total_py  = len(py_list)  # every diagnostic Pyright emitted
    total_pr  = len(pr_list)  # every diagnostic Pyrefly emitted

    # ───── report ───── #
    print("\n================ SUMMARY ================")
    print(f"Total errors in Pyright         : {total_py}")
    print(f"Total errors in Pyrefly         : {total_pr}")
    print(f"Overlapping files               : {len(overlapping_files)}")
    print(f"Overlapping file & row pairs    : {len(overlapping_locs)}")
    print(f"Rows only in Pyright            : {len(py_only_rows)}")
    print(f"Rows only in Pyrefly            : {len(pr_only_rows)}")
    print("=========================================\n")

    # ――― agree‑only mode ――― #
    if args.agree_only:
        if not overlapping_locs:
            print("✅ No rows where both tools agree on an error.")
            return

        print("▶ Rows where Pyright *and* Pyrefly agree:\n")
        for loc in sorted(overlapping_locs):        # loc is "path:row"
            print(f"{loc}:")
            for msg in sorted(py_map[loc]):
                print(f"  Pyright : {msg}")
            for msg in sorted(pr_map[loc]):
                print(f"  Pyrefly : {msg}")
            print()
        return

    if py_only_rows:
        print("▶ PYRIGHT-only locations:")
        for key in sorted(py_only_rows):
            for msg in sorted(py_map[key]):
                print(f"  {key}: {msg}")
        print()

    if pr_only_rows:
        print("▶ PYREFLY-only locations:")
        for key in sorted(pr_only_rows):
            for msg in sorted(pr_map[key]):
                print(f"  {key}: {msg}")
        print()



if __name__ == "__main__":
    main()
