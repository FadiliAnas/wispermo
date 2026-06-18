"""Frozen-app entry point used by PyInstaller.

`multiprocessing.freeze_support()` MUST run first (see below). Client commands
(`wispermo toggle` etc., which the global hotkey runs) are routed BEFORE
importing wispermo.app, so they don't pay the cost of loading PySide6 — keeping
the hotkey snappy.
"""
import multiprocessing
import sys

CLIENT_COMMANDS = {"toggle", "start", "stop", "show", "quit", "status", "ping"}

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if len(sys.argv) > 1 and sys.argv[1] in CLIENT_COMMANDS:
        from wispermo.client import send          # light: socket + config only
        print(send(sys.argv[1]))
        sys.exit(0)
    from wispermo.app import main
    sys.exit(main())
