"""Download external tools (CFR decompiler, etc.) for ModForge.

Usage:
    python scripts/download-tools.py
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"

TOOLS = {
    "cfr": {
        "url": "https://github.com/leibnitz27/cfr/releases/download/0.152/cfr-0.152.jar",
        "filename": "cfr.jar",
        "dir": "cfr",
    },
}


def download_tool(name: str, info: dict) -> None:
    tool_dir = TOOLS_DIR / info["dir"]
    tool_dir.mkdir(parents=True, exist_ok=True)
    target = tool_dir / info["filename"]

    if target.exists():
        print(f"  {name}: already downloaded ({target})")
        return

    print(f"  {name}: downloading from {info['url']}...")
    urllib.request.urlretrieve(info["url"], target)  # noqa: S310 -- trusted URL
    print(f"  {name}: saved to {target}")


def main():
    print("Downloading ModForge tools...")
    for name, info in TOOLS.items():
        try:
            download_tool(name, info)
        except Exception as e:
            print(f"  ERROR downloading {name}: {e}", file=sys.stderr)
    print("Done.")


if __name__ == "__main__":
    main()
