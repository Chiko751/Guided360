"""Steam accounts of this device and switching between them (importable without Decky).

Accounts come from Steam's own config/loginusers.vdf. Steam has no public call to switch the signed-in account, so a
switch follows the same steps the desktop client's own restart does: shut Steam down, set AutoLoginUser in
registry.vdf while Steam is not running (it rewrites that file when it exits), and let the session start Steam again.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from typing import Any

_TOKEN = re.compile(r'"((?:[^"\\]|\\.)*)"|([{}])')


def parse_vdf(text: str) -> dict[str, Any]:
    """Valve KeyValues text to nested dicts (duplicate keys keep the last value)."""
    root: dict[str, Any] = {}
    stack = [root]
    key: str | None = None
    for match in _TOKEN.finditer(text):
        string, brace = match.group(1), match.group(2)
        if brace == "{":
            child: dict[str, Any] = {}
            if key is not None:
                stack[-1][key] = child
            stack.append(child)
            key = None
        elif brace == "}":
            if len(stack) > 1:
                stack.pop()
            key = None
        else:
            value = string.replace('\\"', '"').replace("\\\\", "\\")
            if key is None:
                key = value
            else:
                stack[-1][key] = value
                key = None
    return root


def steam_roots(home: str) -> list[str]:
    candidates = [
        os.path.join(home, ".local", "share", "Steam"),
        os.path.join(home, ".steam", "steam"),
        os.path.join(home, ".steam", "root"),
        os.path.join(home, ".var", "app", "com.valvesoftware.Steam", ".local", "share", "Steam"),
    ]
    seen: list[str] = []
    for path in candidates:
        real = os.path.realpath(path)
        if os.path.isdir(real) and real not in seen:
            seen.append(real)
    return seen


def _loginusers_path(home: str) -> str | None:
    for root in steam_roots(home):
        path = os.path.join(root, "config", "loginusers.vdf")
        if os.path.isfile(path):
            return path
    return None


def list_accounts(home: str) -> list[dict[str, Any]]:
    """[{steamId, account, persona, mostRecent}] for every account that signed in here, most recent first."""
    path = _loginusers_path(home)
    if not path:
        return []
    with open(path, encoding="utf-8", errors="replace") as handle:
        users = parse_vdf(handle.read())
    section = next((v for k, v in users.items() if k.lower() == "users" and isinstance(v, dict)), {})
    accounts = []
    for steam_id, entry in section.items():
        if not isinstance(entry, dict):
            continue
        account = str(entry.get("AccountName", "")).strip()
        if not account:
            continue
        try:
            stamp = int(entry.get("Timestamp", 0))
        except ValueError:
            stamp = 0
        accounts.append({
            "steamId": str(steam_id),
            "account": account,
            "persona": str(entry.get("PersonaName", "")).strip() or account,
            "mostRecent": str(entry.get("MostRecent", "0")) == "1",
            "_stamp": stamp,
        })
    accounts.sort(key=lambda a: (not a["mostRecent"], -a["_stamp"]))
    for a in accounts:
        del a["_stamp"]
    return accounts


def _registry_path(home: str) -> str | None:
    for path in (os.path.join(home, ".steam", "registry.vdf"), os.path.join(home, ".steam", "steam", "registry.vdf")):
        if os.path.isfile(path):
            return path
    return None


_AUTO = re.compile(r'^(\s*)"AutoLoginUser"(\s+)"[^"]*"', re.MULTILINE)
_REMEMBER = re.compile(r'^(\s*)"RememberPassword"(\s+)"[^"]*"', re.MULTILINE)


def set_auto_login(registry_text: str, account: str) -> str:
    """registry.vdf text with Steam's AutoLoginUser set to `account` (and RememberPassword kept on)."""
    if not re.fullmatch(r"[A-Za-z0-9_.\-@]{1,64}", account):
        raise ValueError("unexpected account name")
    if _AUTO.search(registry_text):
        out = _AUTO.sub(lambda m: f'{m.group(1)}"AutoLoginUser"{m.group(2)}"{account}"', registry_text, count=1)
    else:
        steam = re.search(r'^(\s*)"Steam"\s*\n\s*\{\s*\n', registry_text, re.MULTILINE)
        if not steam:
            raise ValueError("registry.vdf has no Steam section")
        indent = steam.group(1) + "\t"
        out = registry_text[: steam.end()] + f'{indent}"AutoLoginUser"\t\t"{account}"\n' + registry_text[steam.end():]
    if _REMEMBER.search(out):
        out = _REMEMBER.sub(lambda m: f'{m.group(1)}"RememberPassword"{m.group(2)}"1"', out, count=1)
    return out


def _steam_running() -> bool:
    try:
        return subprocess.run(["pgrep", "-x", "steam"], capture_output=True, timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def write_auto_login(home: str, account: str) -> bool:
    path = _registry_path(home)
    if not path:
        return False
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    updated = set_auto_login(text, account)
    backup = path + ".guided.bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
    temp = path + ".guided.tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        handle.write(updated)
    shutil.copymode(path, temp)
    os.replace(temp, path)
    return True


def shutdown_command(home: str, user: str | None) -> tuple[list[str], dict[str, str]]:
    steam = shutil.which("steam") or "/usr/bin/steam"
    env = dict(os.environ, HOME=home)
    if hasattr(os, "geteuid") and os.geteuid() == 0 and user:
        return ["runuser", "-u", user, "--", steam, "-shutdown"], env
    return [steam, "-shutdown"], env


def switch_account(home: str, user: str | None, account: str, wait_s: float = 45.0, poll_s: float = 0.4) -> bool:
    """Shuts Steam down, waits for it to exit, sets the auto-login account. Steam then starts as that account."""
    known = {a["account"] for a in list_accounts(home)}
    if account not in known:
        raise ValueError("unknown account")
    command, env = shutdown_command(home, user)
    subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.monotonic() + wait_s
    time.sleep(1.0)
    while _steam_running():
        if time.monotonic() > deadline:
            return False
        time.sleep(poll_s)
    return write_auto_login(home, account)
