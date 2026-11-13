"""Power actions for Guided's own power view: sleep, restart, shut down, switch to the desktop session.

Steam's own power menu cannot be opened from inside the guide (it closes it), so these call logind directly. A
polkit-authorised local session may do this without a password, as it does on SteamOS and Bazzite.
"""

import shutil
import subprocess

ACTIONS = {"sleep": "suspend", "restart": "reboot", "shutdown": "poweroff"}
DESKTOP_COMMANDS = (["steamos-session-select", "plasma"], ["steamos-session-select", "desktop"])


def capabilities():
    """Actions this machine offers, in display order."""
    out = ["sleep", "restart", "shutdown"]
    if shutil.which("steamos-session-select"):
        out.append("desktop")
    return out


def _spawn(command):
    try:
        subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True
    except OSError:
        return False


def run(action, log=lambda _reason: None):
    """Start `action` without waiting for it (suspend only returns on resume). True when a command was started."""
    if action == "desktop":
        for command in DESKTOP_COMMANDS:
            if shutil.which(command[0]) and _spawn(command):
                return True
        log("no session switcher")
        return False
    verb = ACTIONS.get(action)
    if verb is None:
        log("unknown action")
        return False
    for tool in ("systemctl", "loginctl"):
        if shutil.which(tool) and _spawn([tool, verb]):
            return True
    log("no systemctl/loginctl")
    return False
