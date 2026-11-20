"""Context item: "Save to recordings" on a guide programme."""

import os
import sys

import xbmcaddon

sys.path.insert(
    0, os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "lib")
)

from catchup import guide  # noqa: E402

guide.save(getattr(sys, "listitem", None))
