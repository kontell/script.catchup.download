#!/usr/bin/env python3
"""Build a Kodi-installable zip: tools/build.py [OUTDIR] (default ./dist)."""

import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON_ID = "script.catchup.download"
INCLUDE = ["addon.xml", "changelog.txt", "LICENSE.txt", "context.py", "default.py", "resources"]


def main() -> int:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist")
    version = re.search(r'<addon [^>]*version="([^"]+)"', open(os.path.join(ROOT, "addon.xml")).read()).group(1)
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, "%s-%s.zip" % (ADDON_ID, version))
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in INCLUDE:
            path = os.path.join(ROOT, entry)
            if os.path.isfile(path):
                zf.write(path, os.path.join(ADDON_ID, entry))
                continue
            for folder, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for name in files:
                    full = os.path.join(folder, name)
                    zf.write(full, os.path.join(ADDON_ID, os.path.relpath(full, ROOT)))
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
