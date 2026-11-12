"""Media Player tab (1.36): Spotify (the installed desktop app, controlled over MPRIS, playlists read from its own UI
through Chromium's debugger) and YouTube Music (a tiny Steam BrowserView the frontend creates; controlled through Steam's
CEF debugger on port 8080). stdlib only; every call is blocking and meant for asyncio.to_thread."""
import base64
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import urllib.request

STEAM_CDP = 8080
SPOTIFY_CDP = 9229
MPRIS = "org.mpris.MediaPlayer2.spotify"
FLATPAK_ID = "com.spotify.Client"


# --- minimal Chrome DevTools client ---------------------------------------------------------------------------------
class _WS:
    def __init__(self, port: int, path: str, timeout: float = 8.0):
        self.s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.s.recv(1)
            if not chunk:
                raise ConnectionError("devtools handshake closed")
            head += chunk
        if b" 101 " not in head.split(b"\r\n")[0]:
            raise ConnectionError("devtools handshake failed")
        self.buf = b""

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass

    def send(self, obj) -> None:
        data = json.dumps(obj).encode()
        n = len(data)
        hdr = bytes([0x81])
        if n < 126:
            hdr += bytes([0x80 | n])
        elif n < 65536:
            hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        self.s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.s.recv(65536)
            if not chunk:
                raise ConnectionError("devtools closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self):
        msg = b""
        while True:
            b0, b1 = self._read(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n)
            op = b0 & 0x0F
            if op == 8:
                raise ConnectionError("devtools closed")
            if op in (9, 10):
                continue
            msg += payload
            if b0 & 0x80:
                return json.loads(msg)


def _targets(port: int):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=3) as r:
        return json.load(r)


def _page(port: int, match) -> dict | None:
    try:
        return next((t for t in _targets(port) if t.get("type") == "page" and match(t)), None)
    except (OSError, ValueError):
        return None


def cdp_eval(port: int, match, expression: str, timeout: float = 10.0):
    """Evaluate an expression (awaiting promises) in the first page target `match` accepts; None if there is none."""
    target = _page(port, match)
    if not target:
        return None
    ws = _WS(port, "/devtools/page/" + target["webSocketDebuggerUrl"].rsplit("/", 1)[1], timeout)
    try:
        ws.send({"id": 1, "method": "Runtime.evaluate",
                 "params": {"expression": expression, "awaitPromise": True, "returnByValue": True}})
        while True:
            msg = ws.recv()
            if msg.get("id") == 1:
                res = msg.get("result", {})
                if "exceptionDetails" in res:
                    raise RuntimeError(str(res["exceptionDetails"].get("exception", {}).get("description", "error"))[:300])
                return res.get("result", {}).get("value")
    finally:
        ws.close()


# --- Spotify ---------------------------------------------------------------------------------------------------------
def _user_env() -> dict:
    env = dict(os.environ)
    uid = os.getuid()
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{uid}")
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{uid}/bus")
    env.setdefault("DISPLAY", ":0")
    return env


def _busctl(*args: str, timeout: float = 4.0) -> str:
    r = subprocess.run(["busctl", "--user", *args], capture_output=True, text=True, timeout=timeout, env=_user_env())
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:200])
    return r.stdout


def _prop(name: str):
    out = _busctl("--json=short", "get-property", MPRIS, "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player", name)
    return json.loads(out).get("data")


def _spotify_cmd() -> list | None:
    if shutil.which("flatpak"):
        r = subprocess.run(["flatpak", "info", FLATPAK_ID], capture_output=True, timeout=5, env=_user_env())
        if r.returncode == 0:
            return ["flatpak", "run", FLATPAK_ID]
    exe = shutil.which("spotify")
    return [exe] if exe else None


def _spotify_running() -> bool:
    try:
        _busctl("status", MPRIS, timeout=2)
        return True
    except Exception:
        return False


def _spotify_user() -> str | None:
    for base in ("~/.var/app/com.spotify.Client/config/spotify/prefs", "~/.config/spotify/prefs"):
        try:
            with open(os.path.expanduser(base), encoding="utf-8") as f:
                m = re.search(r'autologin\.canonical_username="([^"]+)"', f.read())
                if m:
                    return m.group(1)
        except OSError:
            continue
    return None


def spotify_state() -> dict:
    """installed / running / debuggable (playlists readable) plus the current track."""
    cmd = _spotify_cmd()
    state = {"installed": bool(cmd), "running": _spotify_running(), "library": False}
    if not state["running"]:
        return state
    state["library"] = _page(SPOTIFY_CDP, lambda t: "xpui" in t.get("url", "")) is not None
    try:
        md = _prop("Metadata") or {}
        get = lambda k: (md.get(k) or {}).get("data")
        artists = get("xesam:artist") or []
        state.update({
            "status": _prop("PlaybackStatus"),
            "title": get("xesam:title") or "",
            "artist": ", ".join(artists) if isinstance(artists, list) else str(artists),
            "album": get("xesam:album") or "",
            "art": get("mpris:artUrl") or "",
            "length": int(get("mpris:length") or 0) // 1000,
            "position": int(_prop("Position") or 0) // 1000,
        })
    except Exception:
        pass
    return state


def spotify_start(restart: bool = False) -> dict:
    """Start Spotify in the background (gamescope keeps Steam focused, so its window stays hidden). With `restart` a
    running Spotify without the debug port is restarted so its playlists become readable."""
    cmd = _spotify_cmd()
    if not cmd:
        return {"ok": False, "error": "not-installed"}
    if _spotify_running():
        if not restart:
            return {"ok": True}
        subprocess.run(["pkill", "-x", "spotify"], timeout=5)
        for _ in range(20):
            if not _spotify_running():
                break
            subprocess.run(["sleep", "0.3"])
    subprocess.Popen(cmd + [f"--remote-debugging-port={SPOTIFY_CDP}"], env=_user_env(), stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"ok": True, "started": True}


def spotify_control(action: str, uri: str = "") -> dict:
    method = {"toggle": "PlayPause", "play": "Play", "pause": "Pause", "next": "Next", "prev": "Previous"}.get(action)
    if action == "open":
        if uri == "liked":
            user = _spotify_user()
            uri = f"spotify:user:{user}:collection" if user else "spotify:collection:tracks"
        if not re.fullmatch(r"spotify:[A-Za-z0-9:._-]+", uri or ""):
            return {"ok": False, "error": "bad-uri"}
        _busctl("call", MPRIS, "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player", "OpenUri", "s", uri)
        return {"ok": True}
    if not method:
        return {"ok": False, "error": "bad-action"}
    if action == "pause" and not _spotify_running():
        return {"ok": True}
    _busctl("call", MPRIS, "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player", method)
    return {"ok": True}


_SPOTIFY_LIBRARY_JS = r"""JSON.stringify([...document.querySelectorAll('[role=row]')].map(r => {
  const l = r.querySelector('[aria-labelledby^="listrow-title-"]');
  if (!l) return null;
  const img = r.querySelector('img')?.src || '';
  const uri = l.getAttribute('aria-labelledby').replace('listrow-title-', '').split(' ')[0];
  return { uri: /liked-songs/.test(img) ? 'liked' : uri, name: r.querySelector('[data-encore-id=listRowTitle]')?.textContent?.trim() || '',
           sub: r.querySelector('[data-encore-id=listRowSubtitle]')?.textContent?.trim() || '', img };
}).filter(x => x && x.name))"""


def spotify_library() -> list | None:
    raw = cdp_eval(SPOTIFY_CDP, lambda t: "xpui" in t.get("url", ""), _SPOTIFY_LIBRARY_JS)
    if raw is None:
        return None
    seen, out = set(), []
    for item in json.loads(raw):
        if item["uri"] in seen:
            continue
        seen.add(item["uri"])
        # "PinnedPlaylist • Name" -> "Playlist • Name"
        item["sub"] = re.sub(r"^Pinned", "", item.get("sub", ""))
        out.append(item)
    return out


# --- YouTube Music (page lives in the frontend's BrowserView) -------------------------------------------------------
def _is_ytm(t) -> bool:
    return t.get("url", "").startswith("https://music.youtube.com/")


_YT_STATE_JS = r"""(() => {
  const v = document.querySelector('video'), m = navigator.mediaSession?.metadata;
  const art = m?.artwork?.length ? m.artwork[m.artwork.length - 1].src : '';
  return JSON.stringify({ logged: !!window.ytcfg?.get?.('LOGGED_IN'), url: location.pathname + location.search,
    status: !v || !m ? 'Stopped' : v.paused ? 'Paused' : 'Playing', title: m?.title || '', artist: m?.artist || '',
    album: m?.album || '', art, position: v ? Math.round(v.currentTime * 1000) : 0,
    length: v && isFinite(v.duration) ? Math.round(v.duration * 1000) : 0 });
})()"""

_YT_LIBRARY_JS = r"""(async () => {
  const sap = (document.cookie.match(/(?:^|; )(?:__Secure-3PAPISID|SAPISID)=([^;]+)/) || [])[1];
  const h = { 'Content-Type': 'application/json', 'X-Goog-AuthUser': '0', 'X-Origin': location.origin };
  if (sap) {
    const ts = Math.floor(Date.now() / 1000);
    const d = await crypto.subtle.digest('SHA-1', new TextEncoder().encode(ts + ' ' + sap + ' ' + location.origin));
    h.Authorization = 'SAPISIDHASH ' + ts + '_' + [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, '0')).join('');
  }
  const logged = !!window.ytcfg?.get?.('LOGGED_IN');
  const browse = async (id) => (await fetch('/youtubei/v1/browse?prettyPrint=false', { method: 'POST', credentials: 'include',
    headers: h, body: JSON.stringify({ context: ytcfg.get('INNERTUBE_CONTEXT'), browseId: id }) })).json();
  const out = [], seen = new Set();
  const walk = (o) => {
    if (!o || typeof o !== 'object') return;
    const x = o.musicTwoRowItemRenderer;
    if (x) {
      const s = JSON.stringify(x), pl = (s.match(/"playlistId":"([^"]+)"/) || [])[1];
      const thumbs = x.thumbnailRenderer?.musicThumbnailRenderer?.thumbnail?.thumbnails || [];
      if (pl && !seen.has(pl)) { seen.add(pl); out.push({ uri: pl, name: (x.title?.runs || []).map(r => r.text).join(''),
        sub: (x.subtitle?.runs || []).map(r => r.text).join(''), img: thumbs.length ? thumbs[thumbs.length - 1].url : '' }); }
      return;
    }
    for (const k in o) walk(o[k]);
  };
  walk(await browse(logged ? 'FEmusic_liked_playlists' : 'FEmusic_home'));
  return JSON.stringify({ logged, items: out.slice(0, 60) });
})()"""


def yt_state() -> dict:
    raw = cdp_eval(STEAM_CDP, _is_ytm, _YT_STATE_JS)
    if raw is None:
        consent = _page(STEAM_CDP, lambda t: "consent.youtube.com" in t.get("url", ""))
        return {"page": False, "consent": bool(consent)}
    st = json.loads(raw)
    st["page"] = True
    return st


def yt_library():
    raw = cdp_eval(STEAM_CDP, _is_ytm, _YT_LIBRARY_JS, timeout=15)
    return None if raw is None else json.loads(raw)


def yt_control(action: str, uri: str = "") -> dict:
    if action == "open":
        if not re.fullmatch(r"[A-Za-z0-9_-]{2,80}", uri or ""):
            return {"ok": False, "error": "bad-id"}
        js = f"(location.href = 'https://music.youtube.com/watch?list={uri}', true)"
    elif action == "pause":
        js = "(() => { const v = document.querySelector('video'); if (v && !v.paused) v.pause(); return true; })()"
    else:
        sel = {"toggle": ".play-pause-button", "next": ".next-button", "prev": ".previous-button"}.get(action)
        if not sel:
            return {"ok": False, "error": "bad-action"}
        js = f"(() => {{ const b = document.querySelector('ytmusic-player-bar {sel}'); if (!b) return false; b.click(); return true; }})()"
    ok = cdp_eval(STEAM_CDP, _is_ytm, js)
    return {"ok": bool(ok)}
