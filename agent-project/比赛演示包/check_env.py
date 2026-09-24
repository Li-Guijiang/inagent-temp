# -*- coding: utf-8 -*-
"""Competition 188 - offline environment checker (ASCII-only output).

Called by run_demo.bat BEFORE starting services, so that a missing
python/flask/openpyxl is detected with a clear message instead of a
cryptic ImportError mid-demo.

Checks:
  1) Python present (>= 3.6)
  2) flask installed  (needed by dynamic MCP service on port 5000)
  3) openpyxl installed (needed by skill packages Excel ledger)

Exit code 0 = ready. Non-zero = fix required (see install_deps.bat).
Run:  python check_env.py
"""
import sys


def main():
    print("=" * 60)
    print("  Competition 188 - Smart Manufacturing Demo")
    print("  Environment Check")
    print("=" * 60)

    # 1. Python
    print("[1/3] Python .......... ", end="", flush=True)
    ver = sys.version_info
    if ver.major < 3 or (ver.major == 3 and ver.minor < 6):
        print("FAIL (need >= 3.6)")
        print("      -> Install Python 3.6+ and tick 'Add to PATH'.")
        return 1
    print("OK (" + sys.version.split()[0] + ")")

    # 2. flask
    print("[2/3] flask ........... ", end="", flush=True)
    try:
        import flask  # noqa
        print("OK")
    except Exception:
        print("MISSING")
        print("      -> Double-click install_deps.bat, or run:")
        print("         pip install flask")
        return 2

    # 3. openpyxl
    print("[3/3] openpyxl ........ ", end="", flush=True)
    try:
        import openpyxl  # noqa
        print("OK")
    except Exception:
        print("MISSING")
        print("      -> Double-click install_deps.bat, or run:")
        print("         pip install openpyxl")
        return 3

    print("=" * 60)
    print("  ALL CHECKS PASSED - ready to start the demo!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())