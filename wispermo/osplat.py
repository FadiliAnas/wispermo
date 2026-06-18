"""Tiny OS-platform helper so the rest of the app can branch cleanly."""
from __future__ import annotations

import sys

IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")
IS_WINDOWS = sys.platform.startswith("win")
