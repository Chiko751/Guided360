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
            "volume": round(float(_prop("Volume") or 0) * 100),
            "shuffle": bool(_prop("Shuffle")),
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


_PLAYER = (MPRIS, "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player")


def spotify_control(action: str, uri: str = "") -> dict:
    if action in ("stop", "shuffle", "volume") and not _spotify_running():
        return {"ok": False, "error": "not-running"}
    if action == "stop":  # Spotify's own Stop does nothing visible: pause and rewind
        _busctl("call", *_PLAYER, "Pause")
        _busctl("call", *_PLAYER, "Seek", "x", "--", "-100000000000")
        return {"ok": True}
    if action == "shuffle":
        on = not bool(_prop("Shuffle"))
        _busctl("set-property", *_PLAYER, "Shuffle", "b", "true" if on else "false")
        return {"ok": True, "shuffle": on}
    if action == "volume":
        try:
            vol = max(0, min(100, int(float(uri))))
        except ValueError:
            return {"ok": False, "error": "bad-volume"}
        _busctl("set-property", *_PLAYER, "Volume", "d", str(vol / 100))
        return {"ok": True, "volume": vol}
    method = {"toggle": "PlayPause", "play": "Play", "pause": "Pause", "next": "Next", "prev": "Previous"}.get(action)
    if action == "track":
        ctx, track, uid = (uri.split("\n") + ["", "", ""])[:3]
        if ctx == "liked":
            ctx = _liked_uri()
        if not re.fullmatch(r"spotify:[A-Za-z0-9:._-]+", ctx) or not re.fullmatch(r"spotify:(track|episode):[A-Za-z0-9]+", track) or not re.fullmatch(r"[A-Za-z0-9]*", uid):
            return {"ok": False, "error": "bad-uri"}
        return {"ok": bool(_sp_eval(_SP_PLAY_TRACK_JS + f"({json.dumps(ctx)}, {json.dumps(track)}, {json.dumps(uid)})"))}
    if action == "open":
        if uri == "liked":
            uri = _liked_uri()
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


# Spotify's own platform API (the object its React tree hands around, the same one Spicetify uses): library, playlist
# and album tracks, and playing one track inside its playlist/album. Found by walking the React fibers once.
_SP_PLATFORM_JS = r"""const gxSp = (() => {
  let p = window.__gxPlat;
  if (!p?.getRegistry) {
    p = null;
    const el = [...document.querySelectorAll('body *')].find(e => Object.keys(e).some(k => k.startsWith('__reactFiber$')));
    let f = el && el[Object.keys(el).find(k => k.startsWith('__reactFiber$'))];
    while (f?.return) f = f.return;
    const stack = f ? [f] : [];
    while (stack.length && !p) { const x = stack.pop(); const v = x.memoizedProps?.value;
      if (v && typeof v === 'object' && typeof v.getCollectionPlatformAPI === 'function' && typeof v.getRegistry === 'function') p = v;
      if (x.child) stack.push(x.child); if (x.sibling) stack.push(x.sibling); }
    window.__gxPlat = p;
  }
  if (!p) return null;
  const reg = p.getRegistry(), api = (n) => reg.resolve([...reg._map.keys()].find(k => k.description === n));
  return { p, api };
})();
const gxImg = (u) => { const m = /^spotify:(?:image|mosaic):([0-9a-f]{20,})/.exec(u || ''); return m ? 'https://i.scdn.co/image/' + m[1] : (u || ''); };
"""

_SP_LIBRARY_API_JS = _SP_PLATFORM_JS + r"""(async () => {
  if (!gxSp) return null;
  const lib = gxSp.api('LibraryAPI');
  const out = [{ uri: 'liked', kind: 'liked', name: 'Lieblingssongs', sub: 'Playlist', img: 'https://misc.scdn.co/liked-songs/liked-songs-300.png' }];
  const add = async (folderUri) => {
    const r = await lib.getContents({ limit: 400, offset: 0, ...(folderUri ? { folderUri } : {}) });
    for (const i of r.items || []) {
      if (i.type === 'folder') { await add(i.uri); continue; }
      const kind = i.type === 'your-episodes' ? 'playlist' : i.type;
      const by = i.type === 'album' ? (i.artists || []).map(a => a.name).join(', ') : i.type === 'show' ? (i.publisher || '') : (i.owner?.name || i.madeForName || '');
      const label = { playlist: 'Playlist', album: 'Album', artist: 'Künstler', show: 'Podcast' }[kind] || '';
      out.push({ uri: i.uri, kind, name: i.name || '', by, sub: [label, by].filter(Boolean).join(' • '), img: gxImg(i.images?.[0]?.url) });
    }
  };
  await add(null);
  return JSON.stringify(out);
})()"""

_SP_TRACKS_JS = _SP_PLATFORM_JS + r"""(async (uri) => {
  if (!gxSp) return null;
  const row = (t, uid) => ({ uri: t.uri, uid: uid || t.uid || '', name: t.name || '', sub: (t.artists || []).map(a => a.name || a.profile?.name).filter(Boolean).join(', '),
    ms: t.duration?.milliseconds ?? t.duration?.totalMilliseconds ?? 0, img: gxImg(t.album?.images?.[0]?.url) });
  if (uri === 'liked') {
    const r = await gxSp.api('LibraryAPI').getTracks({ limit: 400, offset: 0 });
    return JSON.stringify((r.items || []).map(t => row(t)));
  }
  if (uri.startsWith('spotify:playlist:')) {
    const r = await gxSp.api('PlaylistAPI').getContents(uri, { limit: 400, offset: 0 });
    return JSON.stringify((r.items || []).filter(t => t.type === 'track' || t.type === 'episode').map(t => row(t)));
  }
  if (uri.startsWith('spotify:album:')) {
    let hash = window.__gxAlbumHash;
    if (!hash) for (const id in window.__webpack_modules__ || {}) { const m = String(window.__webpack_modules__[id]).match(/"queryAlbumTracks","query","([0-9a-f]{64})"/); if (m) { hash = window.__gxAlbumHash = m[1]; break; } }
    if (!hash) return null;
    const r = await gxSp.p.getGraphQLLoader()({ name: 'queryAlbumTracks', operation: 'query', sha256Hash: hash, value: null }, { uri, offset: 0, limit: 300, locale: '' });
    return JSON.stringify((r?.data?.albumUnion?.tracksV2?.items || []).map(x => ({ ...row({ ...x.track, artists: x.track.artists?.items }), uid: x.uid || '' })));
  }
  return null;
})"""

_SP_PLAY_TRACK_JS = _SP_PLATFORM_JS + r"""(async (ctx, uri, uid) => {
  if (!gxSp) return false;
  await gxSp.api('PlayerAPI').play({ uri: ctx }, {}, { skipTo: uid ? { uri, uid } : { uri } });
  return true;
})"""


def _sp_eval(expr: str, timeout: float = 20.0):
    # a block so the helper consts do not collide between evaluations; its last expression is the result
    return cdp_eval(SPOTIFY_CDP, lambda t: "xpui" in t.get("url", ""), "{\n" + expr + "\n}", timeout)


def _liked_uri() -> str:
    user = _spotify_user()
    return f"spotify:user:{user}:collection" if user else "spotify:collection:tracks"


def spotify_tracks(uri: str) -> list | None:
    if uri != "liked" and not re.fullmatch(r"spotify:(playlist|album):[A-Za-z0-9]+", uri or ""):
        return None
    raw = _sp_eval(_SP_TRACKS_JS + f"({json.dumps(uri)})")
    return None if raw is None else json.loads(raw)


def spotify_library() -> list | None:
    try:
        raw = _sp_eval(_SP_LIBRARY_API_JS)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    # fallback: read the rows of its library sidebar
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
        item["kind"] = "liked" if item["uri"] == "liked" else item["uri"].split(":")[1] if item["uri"].count(":") >= 2 else ""
        # Spotify's internal image URIs (spotify:image:<id>, spotify:mosaic:<id>:<id>...) -> its CDN
        m = re.match(r"spotify:(?:image|mosaic):([0-9a-f]{20,})", item.get("img", ""))
        if m:
            item["img"] = "https://i.scdn.co/image/" + m.group(1)
        out.append(item)
    return out


# --- YouTube Music (page lives in the frontend's BrowserView) -------------------------------------------------------
def _is_ytm(t) -> bool:
    return t.get("url", "").startswith("https://music.youtube.com/")


_yt_id = None
_yt_dead: set = set()  # views whose page stopped answering (skipped; the frontend replaces its view)
_yt_slow: dict = {}


def _yt_timeout(page_id: str) -> None:
    _yt_slow[page_id] = _yt_slow.get(page_id, 0) + 1
    if _yt_slow[page_id] >= 2:
        _yt_dead.add(page_id)


def _yt_pages() -> list:
    try:
        return [t for t in _targets(STEAM_CDP) if t.get("type") == "page" and _is_ytm(t)]
    except (OSError, ValueError):
        return []


def _yt_ours():
    """Match for the guide's own YouTube Music view: the tiny one (Steam's web browser may have YouTube Music open too)."""
    global _yt_id
    pages = _yt_pages()
    if _yt_id and any(t["id"] == _yt_id for t in pages):
        return lambda t: t.get("id") == _yt_id
    _yt_id = None
    for t in pages:
        if t["id"] in _yt_dead:
            continue
        try:
            if (cdp_eval(STEAM_CDP, lambda x, i=t["id"]: x.get("id") == i, "innerWidth", 4) or 9999) < 50:
                _yt_id = t["id"]
                _yt_slow.pop(_yt_id, None)
                return lambda x: x.get("id") == _yt_id
        except (TimeoutError, socket.timeout):
            _yt_timeout(t["id"])
        except Exception:
            continue
    return lambda t: False


_YT_STATE_JS = r"""(() => {
  const v = document.querySelector('video'), m = navigator.mediaSession?.metadata;
  const art = m?.artwork?.length ? m.artwork[m.artwork.length - 1].src : '';
  return JSON.stringify({ logged: !!window.ytcfg?.get?.('LOGGED_IN'), ready: !!window.ytcfg?.get?.('INNERTUBE_CONTEXT') && document.readyState === 'complete', url: location.pathname + location.search,
    status: !v || !m ? 'Stopped' : v.paused ? 'Paused' : 'Playing', title: m?.title || '', artist: m?.artist || '',
    album: m?.album || '', art, volume: document.querySelector('#movie_player')?.isMuted?.() ? 0 : (document.querySelector('#movie_player')?.getVolume?.() ?? 100), position: v ? Math.round(v.currentTime * 1000) : 0,
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
      if (pl && !seen.has(pl)) { seen.add(pl); out.push({ uri: pl, kind: pl.startsWith('RDAMVM') ? 'radio' : 'ytlist', name: (x.title?.runs || []).map(r => r.text).join(''),
        sub: (x.subtitle?.runs || []).map(r => r.text).join(''), img: thumbs.length ? thumbs[thumbs.length - 1].url : '' }); }
      return;
    }
    for (const k in o) walk(o[k]);
  };
  walk(await browse(logged ? 'FEmusic_liked_playlists' : 'FEmusic_home'));
  return JSON.stringify({ logged, items: out.slice(0, 60) });
})()"""


_YT_TRACKS_JS = r"""(async (list) => {
  const sap = (document.cookie.match(/(?:^|; )(?:__Secure-3PAPISID|SAPISID)=([^;]+)/) || [])[1];
  const h = { 'Content-Type': 'application/json', 'X-Goog-AuthUser': '0', 'X-Origin': location.origin };
  if (sap) {
    const ts = Math.floor(Date.now() / 1000);
    const d = await crypto.subtle.digest('SHA-1', new TextEncoder().encode(ts + ' ' + sap + ' ' + location.origin));
    h.Authorization = 'SAPISIDHASH ' + ts + '_' + [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, '0')).join('');
  }
  const r = await (await fetch('/youtubei/v1/browse?prettyPrint=false', { method: 'POST', credentials: 'include', headers: h,
    body: JSON.stringify({ context: ytcfg.get('INNERTUBE_CONTEXT'), browseId: 'VL' + list }) })).json();
  const out = [], seen = new Set();
  const text = (c) => (c?.musicResponsiveListItemFlexColumnRenderer?.text?.runs || []).map(x => x.text).join('');
  const walk = (o) => {
    if (!o || typeof o !== 'object') return;
    const x = o.musicResponsiveListItemRenderer;
    if (x) {
      const vid = x.playlistItemData?.videoId || (JSON.stringify(x.overlay || {}).match(/"videoId":"([^"]+)"/) || [])[1];
      if (vid && !seen.has(vid)) { seen.add(vid);
        const th = x.thumbnail?.musicThumbnailRenderer?.thumbnail?.thumbnails || [];
        const len = (x.fixedColumns || []).map(c => (c.musicResponsiveListItemFixedColumnRenderer?.text?.runs || []).map(r => r.text).join('')).join('');
        const [m, sec] = (len.match(/(\d+):(\d+)$/) || []).slice(1).map(Number);
        out.push({ uri: vid, uid: '', name: text(x.flexColumns?.[0]), sub: text(x.flexColumns?.[1]), ms: m >= 0 ? (m * 60 + sec) * 1000 : 0, img: th.length ? th[0].url : '' }); }
      return;
    }
    for (const k in o) walk(o[k]);
  };
  walk(r);
  return JSON.stringify(out.slice(0, 300));
})"""


def yt_tracks(list_id: str) -> list | None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,80}", list_id or ""):
        return None
    raw = cdp_eval(STEAM_CDP, _yt_ours(), _YT_TRACKS_JS + f"({json.dumps(list_id)})", 15)
    return None if raw is None else json.loads(raw)


def yt_state() -> dict:
    global _yt_id
    ours = _yt_ours()
    try:
        raw = cdp_eval(STEAM_CDP, ours, _YT_STATE_JS, 6)
    except (TimeoutError, socket.timeout):
        # the page hangs (seen once after a plugin reload): after a second time it is skipped, and the frontend
        # creates a new view once it has seen no page for a while
        if _yt_id:
            _yt_timeout(_yt_id)
            if _yt_id in _yt_dead:
                _yt_id = None
        return {"page": False}
    if _yt_id:
        _yt_slow.pop(_yt_id, None)
    if raw is None:
        consent = _page(STEAM_CDP, lambda t: "consent.youtube.com" in t.get("url", ""))
        return {"page": False, "consent": bool(consent)}
    st = json.loads(raw)
    st["page"] = True
    if st.get("ready") and not st.get("logged") and st.get("url") == "/":
        # signed in meanwhile in Steam's browser (shared cookies): the frontend reloads our view
        for t in _yt_pages():
            if not ours(t):
                try:
                    if cdp_eval(STEAM_CDP, lambda x, i=t["id"]: x.get("id") == i, "!!window.ytcfg?.get?.('LOGGED_IN')", 4):
                        st["otherLogged"] = True
                        break
                except Exception:
                    continue
    return st


def yt_library():
    raw = cdp_eval(STEAM_CDP, _yt_ours(), _YT_LIBRARY_JS, timeout=15)
    return None if raw is None else json.loads(raw)


def yt_control(action: str, uri: str = "") -> dict:
    if action == "track":
        list_id, vid = (uri.split("\n") + ["", ""])[:2]
        if not re.fullmatch(r"[A-Za-z0-9_-]{2,80}", list_id) or not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", vid):
            return {"ok": False, "error": "bad-id"}
        action, uri, target = "open", list_id, f"watch?v={vid}&list={list_id}"
    else:
        target = f"watch?list={uri}"
    if action == "open":
        if not re.fullmatch(r"[A-Za-z0-9_-]{2,80}", uri or ""):
            return {"ok": False, "error": "bad-id"}
        # a new page starts at full volume: carry the current one over
        vol = cdp_eval(STEAM_CDP, _yt_ours(), "(() => { const p = document.querySelector('#movie_player'); return p?.getVolume ? (p.isMuted() ? 0 : p.getVolume()) : null; })()")
        ok = cdp_eval(STEAM_CDP, _yt_ours(), f"(location.href = 'https://music.youtube.com/{target}', true)")
        if isinstance(vol, (int, float)) and vol < 100:
            import time
            for _ in range(24):
                time.sleep(0.25)
                try:
                    if yt_control("volume", str(vol)).get("ok"):
                        break
                except Exception:
                    continue
        return {"ok": bool(ok)}
    elif action == "stop":
        js = "(() => { const v = document.querySelector('video'); if (!v) return false; v.pause(); v.currentTime = 0; return true; })()"
    elif action == "volume":
        try:
            vol = max(0, min(100, int(float(uri))))
        except ValueError:
            return {"ok": False, "error": "bad-volume"}
        js = (f"(() => {{ const p = document.querySelector('#movie_player'); if (!p?.setVolume) return false; p.setVolume({vol}); "
              f"{vol} ? p.unMute() : p.mute(); return true; }})()")
    elif action == "reload":
        js = "(location.href = 'https://music.youtube.com/', true)"
    elif action == "pause":
        js = "(() => { const v = document.querySelector('video'); if (v && !v.paused) v.pause(); return true; })()"
    else:
        sel = {"toggle": ".play-pause-button", "next": ".next-button", "prev": ".previous-button", "shuffle": ".shuffle"}.get(action)
        if not sel:
            return {"ok": False, "error": "bad-action"}
        js = f"(() => {{ const b = document.querySelector('ytmusic-player-bar {sel}'); if (!b) return false; b.click(); return true; }})()"
    ok = cdp_eval(STEAM_CDP, _yt_ours(), js)
    return {"ok": bool(ok)}
