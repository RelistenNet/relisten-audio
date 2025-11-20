#!/usr/bin/env python3
"""
keep_dir_size.py  –  cap one or more directories at MAX_SIZE by evicting the
                     least-recently-accessed files first.

Usage:
  keep_dir_size.py /path/to/dir --max-size 2.5T      # live run
  keep_dir_size.py /var/cache --max-size 500G --dry-run
  keep_dir_size.py /var/cache /tmp/cache 500G        # legacy positional size

This file is deployed on the relisten2 server with a crontab to keep the files under control.

0 * * * * python3 /home/alecgorge/keep_dir_size.py /home/alecgorge/music/archive.org/ /home/alecgorge/music/phish.in/ --max-size 2.4T >> /home/alecgorge/keep_dir_size.log 2>&1
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Sequence, Tuple

# ───────────────────────── helpers ──────────────────────────
_UNITS = {"k": 2**10, "m": 2**20, "g": 2**30, "t": 2**40}

def parse_size(text: str) -> int:
    """Accept '2500G', '2.5T', '1048576' (bytes) … → bytes as int."""
    text = text.strip().lower()
    if text[-1] in _UNITS:
        return int(float(text[:-1]) * _UNITS[text[-1]])
    return int(text)

def format_size(n: int) -> str:
    for suffix, unit in reversed(_UNITS.items()):
        if n >= unit:
            return f"{n / unit:.1f}{suffix.upper()}"
    return f"{n}B"

# ───────────────────────── main logic ───────────────────────
def collect(dir_paths: Sequence[Path]) -> Tuple[int, List[Tuple[float, int, str]]]:
    """Return (total_bytes, [(atime, size, path), …]) across all directories."""
    entries: List[Tuple[float, int, str]] = []
    total = 0
    stack = list(dir_paths)

    while stack:
        p = Path(stack.pop())
        try:
            with os.scandir(p) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            st = entry.stat(follow_symlinks=False)
                            total += st.st_size
                            entries.append((st.st_atime, st.st_size, entry.path))
                    except FileNotFoundError:
                        # File disappeared between readdir and stat; skip.
                        continue
        except PermissionError as e:
            print(f"skip {p}: {e}", file=sys.stderr)
    return total, entries

def evict(dir_paths: Sequence[Path], max_bytes: int, dry_run: bool = False) -> None:
    total, files = collect(dir_paths)
    joined = ", ".join(str(p) for p in dir_paths)
    print(f"Current size across {len(dir_paths)} dir(s) [{joined}]: {format_size(total)}; "
          f"limit: {format_size(max_bytes)}")

    if total <= max_bytes:
        print("Nothing to delete.")
        return

    # Oldest atime first
    files.sort(key=lambda t: t[0])

    deleted = 0
    deleted_size = 0
    for atime, size, path in files:
        atime_dt = datetime.utcfromtimestamp(int(atime)).strftime('%Y-%m-%d %H:%M:%S')

        if total <= max_bytes:
            break
        deleted += 1
        deleted_size += size
        total -= size
        if dry_run:
            print(f"[dry-run] would delete {path} (atime={atime_dt}, size={format_size(size)})")
        else:
            try:
                os.remove(path)
                print(f"deleted {path} (atime={atime_dt}, size={format_size(size)})")
            except FileNotFoundError:
                print(f"already gone: {path}", file=sys.stderr)
            except PermissionError as e:
                print(f"cannot delete {path}: {e}", file=sys.stderr)

    print(f"{'Would free' if dry_run else 'Freed'} {format_size(deleted_size)} "
          f"by removing {deleted} file(s). Final size: {format_size(total)}")

# ───────────────────────── entry point ──────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Cap directory size with LRU eviction")
    ap.add_argument(
        "paths",
        nargs="+",
        help="One or more directories to manage; optionally end with MAX_SIZE for legacy usage",
    )
    ap.add_argument(
        "-m", "--max-size",
        dest="max_size",
        type=parse_size,
        help="Maximum size (e.g. 2.5T, 500G, 1048576)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    args = ap.parse_args()

    if args.max_size is None:
        if len(args.paths) < 2:
            ap.error("Provide --max-size or supply MAX_SIZE as the final positional argument.")
        try:
            max_size = parse_size(args.paths[-1])
        except ValueError as e:
            ap.error(f"Invalid max size {args.paths[-1]!r}: {e}")
        dir_args = args.paths[:-1]
    else:
        max_size = args.max_size
        dir_args = args.paths

    directories = [Path(p) for p in dir_args]
    missing = [p for p in directories if not p.is_dir()]
    if missing:
        ap.error(f"Not a directory: {', '.join(str(p) for p in missing)}")

    evict(directories, max_size, dry_run=args.dry_run)
