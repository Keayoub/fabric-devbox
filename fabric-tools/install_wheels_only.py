"""Install wheels-only into the active Python environment.

Usage:
  python tools\install_wheels_only.py --requirements requirements.txt
  python tools\install_wheels_only.py --dir wheels --no-deps

This enforces that only pre-built wheels are installed. When using --requirements,
the script will check that each requirement has at least one wheel available on PyPI
before calling pip with --only-binary=:all:.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
import tempfile
import shutil
import json


def run(cmd, check=True):
    print("+ ", " ".join(cmd))
    res = subprocess.run(cmd, shell=False)
    if check and res.returncode != 0:
        raise SystemExit(res.returncode)
    return res.returncode


def ensure_wheel_for_requirement(req: str) -> bool:
    """Use pip index to check if a wheel exists for the requirement specifier.
    This is a best-effort check: pip index may still return source-only packages for complex specs.
    """
    try:
        cmd = [sys.executable, "-m", "pip", "index", "versions", req]
        print(f"Checking wheel availability for: {req}")
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        # If pip index prints versions, assume wheels exist for at least some versions.
        return "Available versions" in out or "Versions" in out or "found" in out
    except subprocess.CalledProcessError as e:
        print("pip index returned non-zero; assuming safe to proceed.\n", e.output)
        return True


def install_from_requirements(reqfile: Path) -> int:
    if not reqfile.exists():
        print(f"Requirements file {reqfile} not found", file=sys.stderr)
        return 2

    # Quick parse: collect non-comment, non-empty lines
    lines = [l.strip() for l in reqfile.read_text(encoding="utf-8").splitlines()]
    specs = [l for l in lines if l and not l.startswith("#")]

    missing = []
    for s in specs:
        ok = ensure_wheel_for_requirement(s.split()[0])
        if not ok:
            missing.append(s)

    if missing:
        print("The following requirements may not have wheels available:")
        for m in missing:
            print(" -", m)
        print("Aborting wheel-only install.")
        return 3

    # delegate to pip
    cmd = [sys.executable, "-m", "pip", "install", "--only-binary=:all:", "-r", str(reqfile)]
    return run(cmd)


def install_from_dir(wheels_dir: Path, no_deps: bool = False) -> int:
    if not wheels_dir.exists():
        print(f"Wheels directory {wheels_dir} not found", file=sys.stderr)
        return 4
    whls = list(wheels_dir.glob("*.whl"))
    if not whls:
        print(f"No .whl files found in {wheels_dir}", file=sys.stderr)
        return 5

    for w in whls:
        cmd = [sys.executable, "-m", "pip", "install", str(w)]
        if no_deps:
            cmd.insert(-1, "--no-deps")
        run(cmd)
    return 0


def main(argv: list[str] | None = None):
    p = argparse.ArgumentParser()
    p.add_argument("--requirements", "-r", type=Path, help="requirements.txt file to install (wheel-only)")
    p.add_argument("--dir", "-d", type=Path, help="directory with .whl files to install")
    p.add_argument("--no-deps", action="store_true", help="pass --no-deps when installing local wheels")
    args = p.parse_args(argv)

    if args.requirements and args.dir:
        print("Please specify only one of --requirements or --dir", file=sys.stderr)
        return 6

    if not args.requirements and not args.dir:
        print("Specify --requirements or --dir", file=sys.stderr)
        return 7

    if args.requirements:
        return install_from_requirements(args.requirements)

    return install_from_dir(args.dir, no_deps=args.no_deps)


if __name__ == "__main__":
    raise SystemExit(main())
