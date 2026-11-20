"""Settings buttons: RunScript(script.catchup.download,<action>)."""

import os
import sys

import xbmcaddon

sys.path.insert(
    0, os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "lib")
)

from catchup import account, downloads, serverpicker, settings  # noqa: E402

ACTIONS = {
    "findservers": serverpicker.find_servers,
    "login": account.login,
    "logout": account.logout,
    "downloads": downloads.show,
}

action = ACTIONS.get(sys.argv[1] if len(sys.argv) > 1 else "")
if action is not None:
    action()
else:
    settings.open_settings()
