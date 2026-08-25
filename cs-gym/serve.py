#!/usr/bin/env python3
"""Static server for CS Gym, plus a small endpoint that saves progress to disk.

``python3 -m http.server`` can only read files, so progress lived in the
browser's localStorage and vanished if you cleared it or switched browsers.
This serves the same directory and adds GET/PUT on /progress, which reads and
writes cs-gym/progress.json.  Bound to localhost only -- it accepts writes.
"""

import json
import os
import shutil
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PROGRESS = os.path.join(HERE, "progress.json")
MAX_BODY = 8 * 1024 * 1024


def load_progress():
    if not os.path.exists(PROGRESS):
        return {}
    try:
        with open(PROGRESS) as handle:
            saved = json.load(handle)
    except (ValueError, OSError):
        return {}
    return saved if isinstance(saved, dict) else {}


def merge_progress(old, new):
    """Fold an incoming snapshot into what is already saved.

    Deliberately additive: a problem that exists on disk is never dropped,
    whatever the client sends.  A browser with a half-populated localStorage
    -- one that was just cleared, say -- can then push a thin snapshot without
    taking the rest of the file down with it.  Per problem the newer copy
    wins, so real edits still propagate.
    """
    code = dict(old.get("code") or {})
    code_at = dict(old.get("codeAt") or {})
    for pid, source in (new.get("code") or {}).items():
        when = (new.get("codeAt") or {}).get(pid, 0)
        if pid not in code or when >= code_at.get(pid, 0):
            code[pid] = source
            code_at[pid] = when
    solved = set(old.get("solved") or []) | set(new.get("solved") or [])
    return {
        "version": 1,
        "updated": new.get("updated") or old.get("updated"),
        "last": new.get("last") or old.get("last"),
        "solved": sorted(solved),
        "code": code,
        "codeAt": code_at,
    }


class GymHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def log_message(self, fmt, *args):
        if self.path != "/progress":
            super().log_message(fmt, *args)

    def do_GET(self):
        if self.path == "/progress":
            self._respond(200, json.dumps(load_progress()).encode())
            return
        super().do_GET()

    def do_PUT(self):
        if self.path != "/progress":
            self.send_error(405, "only /progress accepts writes")
            return
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BODY:
            self.send_error(400, "bad body length")
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except ValueError:
            self.send_error(400, "body is not JSON")
            return
        if not isinstance(payload, dict):
            self.send_error(400, "body is not an object")
            return
        merged = merge_progress(load_progress(), payload)
        if os.path.exists(PROGRESS):
            shutil.copyfile(PROGRESS, PROGRESS + ".bak")
        tmp = PROGRESS + ".tmp"
        with open(tmp, "w") as handle:
            json.dump(merged, handle, indent=1, sort_keys=True)
        os.replace(tmp, PROGRESS)
        self._respond(200, json.dumps({
            "ok": True,
            "problems": len(merged["code"]),
            "solved": len(merged["solved"]),
        }).encode())

    # navigator.sendBeacon can only POST, so the unload flush lands here.
    do_POST = do_PUT

    def _respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main():
    port = int(os.environ.get("PORT", "5177"))
    server = ThreadingHTTPServer(("127.0.0.1", port), GymHandler)
    print("CS Gym  ->  http://localhost:%d" % port)
    print("progress ->  %s" % PROGRESS)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
