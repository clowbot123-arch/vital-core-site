#!/usr/bin/env python3
"""
GA4 Coverage Monitor for VitalCore
Lists every HTML page with:
- ✅ green check if GA ID is present
- ❌ red cross if GA ID is missing

Usage:
  python3 tools/ga_monitor.py
  python3 tools/ga_monitor.py --id G-XXXXXXXXXX
  python3 tools/ga_monitor.py --no-color
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

DEFAULT_MEASUREMENT_ID = "G-ZZND0S6EPD"


class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"


def has_ga(html: str, measurement_id: str) -> bool:
    checks = [
        measurement_id,
        f"gtag/js?id={measurement_id}",
        "googletagmanager.com/gtag/js",
        "gtag('config'",
        'gtag("config"',
    ]
    return all([
        measurement_id in html,
        any(c in html for c in checks[1:]),
    ])


def mark(ok: bool, use_color: bool) -> str:
    if ok:
        return f"{Color.GREEN}✅{Color.RESET}" if use_color else "✅"
    return f"{Color.RED}❌{Color.RESET}" if use_color else "❌"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check GA4 snippet coverage across all HTML files.")
    parser.add_argument("--id", default=DEFAULT_MEASUREMENT_ID, help="GA4 Measurement ID (default: G-ZZND0S6EPD)")
    parser.add_argument("--root", default=".", help="Project root directory (default: current directory)")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    use_color = (not args.no_color) and sys.stdout.isatty()

    html_files = sorted(root.rglob("*.html"))
    if not html_files:
        print("No HTML files found.")
        return 1

    ok_files: list[Path] = []
    missing_files: list[Path] = []

    print(f"\nGA4 Monitor — Measurement ID: {args.id}")
    print(f"Project root: {root}\n")

    for file in html_files:
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            rel = file.relative_to(root)
            print(f"{mark(False, use_color)} {rel}  (read error: {e})")
            missing_files.append(file)
            continue

        ok = has_ga(content, args.id)
        rel = file.relative_to(root)
        print(f"{mark(ok, use_color)} {rel}")

        if ok:
            ok_files.append(file)
        else:
            missing_files.append(file)

    total = len(html_files)
    ok_count = len(ok_files)
    missing_count = len(missing_files)

    print("\n" + "-" * 60)
    if use_color:
        print(f"{Color.GREEN}✅ With GA: {ok_count}{Color.RESET}")
        print(f"{Color.RED}❌ Missing GA: {missing_count}{Color.RESET}")
    else:
        print(f"✅ With GA: {ok_count}")
        print(f"❌ Missing GA: {missing_count}")
    print(f"📄 Total HTML files: {total}")
    print("-" * 60)

    if missing_count > 0:
        if use_color:
            print(f"\n{Color.YELLOW}Some pages are missing GA tracking.{Color.RESET}")
        else:
            print("\nSome pages are missing GA tracking.")
        return 2

    print("\nAll pages include the GA tracking ID. 🎉")
    return 0


if __name__ == "__main__":
    sys.exit(main())
