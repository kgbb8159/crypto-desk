#!/usr/bin/env python3
"""시그널 데스크 로컬 서버 + RSS 프록시
실행: python3 server.py
접속: http://127.0.0.1:8787
"""
from __future__ import annotations

import json
import mimetypes
import ssl
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
PORT = 8787
UA = "SignalDeskBot/1.0 (+local rss aggregator)"
REPORTS = ROOT / "reports"
HISTORY = REPORTS / "history"
BRIEFING_INTERVAL_SEC = 8 * 60 * 60
_scheduler_state = {
    "running": False,
    "last_run_at": None,
    "last_ok": None,
    "last_error": "",
    "next_run_at": None,
}
_run_lock = threading.Lock()
_summary_cache: dict[str, dict] = {}
_summary_lock = threading.Lock()


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
        try:
            ctx.load_default_certs()
        except Exception:
            pass
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


def fetch_text(target: str, accept: str = "*/*") -> str:
    req = urllib.request.Request(
        target,
        headers={
            "User-Agent": UA,
            "Accept": accept,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12, context=ssl_context()) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        result = subprocess.run(
            [
                "curl",
                "-fsSL",
                "--max-time",
                "12",
                "-A",
                UA,
                "-H",
                f"Accept: {accept}",
                target,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "fetch failed")
        return result.stdout


def fetch_rss(target: str) -> str:
    return fetch_text(
        target,
        "application/rss+xml, application/xml, text/xml, */*",
    )


def venv_python() -> str:
    venv_py = ROOT / ".venv" / "bin" / "python"
    return str(venv_py) if venv_py.exists() else sys.executable


def archive_latest() -> Path | None:
    latest = REPORTS / "latest.md"
    if not latest.exists():
        return None
    HISTORY.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest = HISTORY / f"briefing-{stamp}.md"
    dest.write_text(latest.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


def run_briefing(dry_run: bool = False) -> dict:
    with _run_lock:
        _scheduler_state["running"] = True
        try:
            cmd = [venv_python(), str(ROOT / "main.py"), "--no-telegram"]
            if dry_run:
                cmd.append("--dry-run")
            result = subprocess.run(
                cmd,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=180,
            )
            latest = REPORTS / "latest.md"
            md = latest.read_text(encoding="utf-8") if latest.exists() else ""
            ok = result.returncode == 0 and bool(md)
            archived = None
            if md:
                archived = archive_latest()
            now = time.time()
            _scheduler_state["last_run_at"] = now
            _scheduler_state["last_ok"] = ok
            _scheduler_state["last_error"] = (
                "" if ok else (result.stderr or result.stdout or "failed")[-500:]
            )
            _scheduler_state["next_run_at"] = now + BRIEFING_INTERVAL_SEC
            return {
                "ok": ok,
                "returncode": result.returncode,
                "stdout": (result.stdout or "")[-2000:],
                "stderr": (result.stderr or "")[-2000:],
                "markdown": md,
                "archived": str(archived) if archived else None,
            }
        except Exception as exc:  # noqa: BLE001
            now = time.time()
            _scheduler_state["last_run_at"] = now
            _scheduler_state["last_ok"] = False
            _scheduler_state["last_error"] = str(exc)
            _scheduler_state["next_run_at"] = now + BRIEFING_INTERVAL_SEC
            return {"ok": False, "error": str(exc), "markdown": ""}
        finally:
            _scheduler_state["running"] = False


def latest_mtime() -> float | None:
    latest = REPORTS / "latest.md"
    if not latest.exists():
        return None
    return latest.stat().st_mtime


def seconds_until_next() -> float:
    nxt = _scheduler_state.get("next_run_at")
    if nxt is None:
        mt = latest_mtime()
        if mt is None:
            return 0
        due = mt + BRIEFING_INTERVAL_SEC
        return max(0, due - time.time())
    return max(0, float(nxt) - time.time())


def briefing_scheduler() -> None:
    time.sleep(3)
    while True:
        try:
            wait = seconds_until_next()
            if wait <= 0:
                print("[briefing] auto-run start")
                out = run_briefing(dry_run=False)
                print(f"[briefing] auto-run done ok={out.get('ok')}")
                wait = BRIEFING_INTERVAL_SEC
            time.sleep(min(wait, 300) or 1)
        except Exception as exc:  # noqa: BLE001
            print(f"[briefing] scheduler error: {exc}")
            time.sleep(60)


def list_history(limit: int = 60) -> list[dict]:
    HISTORY.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    for path in HISTORY.glob("briefing-*.md"):
        st = path.stat()
        items.append(
            {
                "id": path.name,
                "name": path.name,
                "mtime": st.st_mtime,
                "size": st.st_size,
            }
        )
    for path in REPORTS.glob("morning-brief-*.md"):
        st = path.stat()
        items.append(
            {
                "id": path.name,
                "name": path.name,
                "mtime": st.st_mtime,
                "size": st.st_size,
            }
        )
    items.sort(key=lambda x: x["mtime"], reverse=True)
    seen: set[str] = set()
    uniq: list[dict] = []
    for it in items:
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        uniq.append(it)
    return uniq[:limit]


def read_history_file(file_id: str) -> Path | None:
    name = Path(file_id).name
    for base in (HISTORY, REPORTS):
        path = base / name
        if path.exists() and path.is_file() and path.suffix == ".md":
            return path
    return None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/rss":
            return self.handle_rss(parsed.query)
        if parsed.path == "/api/json":
            return self.handle_json(parsed.query)
        if parsed.path == "/api/portfolio":
            return self.handle_portfolio()
        if parsed.path == "/api/briefing/latest":
            return self.handle_briefing_latest()
        if parsed.path == "/api/briefing/history":
            return self.handle_briefing_history(parsed.query)
        if parsed.path == "/api/briefing/item":
            return self.handle_briefing_item(parsed.query)
        if parsed.path == "/api/briefing/status":
            return self.handle_briefing_status()
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/briefing/run":
            return self.handle_briefing_run(parsed.query)
        if parsed.path == "/api/summarize":
            return self.handle_summarize()
        self.send_response(404)
        self.end_headers()

    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(min(length, 200_000))
        try:
            data = json.loads(raw.decode("utf-8", errors="replace"))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"invalid json: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("json object required")
        return data

    def handle_summarize(self):
        try:
            body = self.read_json_body()
        except ValueError as exc:
            return self.json_response(400, {"error": str(exc)})

        article = {
            "title": str(body.get("title") or "").strip()[:400],
            "summary": str(body.get("summary") or "").strip()[:4000],
            "link": str(body.get("link") or "").strip()[:1000],
            "source": str(body.get("source") or "").strip()[:120],
            "category": str(body.get("category") or "").strip()[:40],
            "assets": body.get("assets") if isinstance(body.get("assets"), list) else [],
        }
        if not article["title"]:
            return self.json_response(400, {"error": "title required"})

        cache_key = article["link"] or article["title"]
        with _summary_lock:
            cached = _summary_cache.get(cache_key)
            if cached:
                return self.json_response(200, {**cached, "cached": True})

        try:
            from briefing.config import get_settings
            from briefing.summarizer import summarize_article

            settings = get_settings()
            markdown, mode = summarize_article(settings, article)
            payload = {
                "ok": True,
                "markdown": markdown,
                "mode": mode,
                "title": article["title"],
                "link": article["link"],
                "source": article["source"],
                "cached": False,
            }
            with _summary_lock:
                if len(_summary_cache) > 80:
                    _summary_cache.clear()
                _summary_cache[cache_key] = payload
            return self.json_response(200, payload)
        except Exception as exc:  # noqa: BLE001
            return self.json_response(500, {"error": str(exc)})

    def handle_portfolio(self):
        try:
            from briefing.collectors.onchain import fetch_prices
            from briefing.portfolio import build_portfolio, format_portfolio_section

            prices = fetch_prices()
            portfolio = build_portfolio(prices)
            return self.json_response(
                200,
                {
                    "portfolio": portfolio,
                    "markdown": format_portfolio_section(portfolio),
                },
            )
        except Exception as exc:  # noqa: BLE001
            return self.json_response(500, {"error": str(exc)})

    def handle_briefing_latest(self):
        latest = REPORTS / "latest.md"
        if not latest.exists():
            return self.json_response(
                200,
                {
                    "exists": False,
                    "markdown": "",
                    "hint": "Waiting for auto briefing (every 8 hours).",
                },
            )
        md = latest.read_text(encoding="utf-8")
        return self.json_response(
            200,
            {
                "exists": True,
                "markdown": md,
                "mtime": latest.stat().st_mtime,
                "path": str(latest),
            },
        )

    def handle_briefing_history(self, query: str):
        qs = parse_qs(query)
        try:
            limit = int((qs.get("limit") or ["60"])[0])
        except ValueError:
            limit = 60
        return self.json_response(200, {"items": list_history(limit=limit)})

    def handle_briefing_item(self, query: str):
        qs = parse_qs(query)
        file_id = unquote((qs.get("id") or [""])[0])
        path = read_history_file(file_id)
        if not path:
            return self.json_response(404, {"error": "not found"})
        return self.json_response(
            200,
            {
                "id": path.name,
                "markdown": path.read_text(encoding="utf-8"),
                "mtime": path.stat().st_mtime,
            },
        )

    def handle_briefing_status(self):
        mt = latest_mtime()
        next_at = _scheduler_state.get("next_run_at")
        if next_at is None and mt is not None:
            next_at = mt + BRIEFING_INTERVAL_SEC
        return self.json_response(
            200,
            {
                "interval_hours": 8,
                "running": _scheduler_state["running"],
                "last_run_at": _scheduler_state["last_run_at"] or mt,
                "last_ok": _scheduler_state["last_ok"],
                "last_error": _scheduler_state["last_error"],
                "next_run_at": next_at,
                "seconds_until_next": seconds_until_next(),
            },
        )

    def handle_briefing_run(self, query: str):
        qs = parse_qs(query)
        dry = (qs.get("dry_run") or ["0"])[0] in {"1", "true", "yes"}
        out = run_briefing(dry_run=dry)
        code = 200 if out.get("ok") else 500
        return self.json_response(code, out)

    def handle_rss(self, query: str):
        qs = parse_qs(query)
        target = (qs.get("url") or [None])[0]
        if not target:
            return self.json_response(400, {"error": "url required"})

        parsed = urlparse(target)
        if parsed.scheme not in ("http", "https"):
            return self.json_response(400, {"error": "invalid protocol"})

        try:
            xml = fetch_rss(target)
            return self.json_response(200, {"xml": xml})
        except Exception as exc:  # noqa: BLE001
            return self.json_response(502, {"error": str(exc)})

    def handle_json(self, query: str):
        qs = parse_qs(query)
        target = (qs.get("url") or [None])[0]
        if not target:
            return self.json_response(400, {"error": "url required"})

        parsed = urlparse(target)
        if parsed.scheme not in ("http", "https"):
            return self.json_response(400, {"error": "invalid protocol"})

        host = (parsed.hostname or "").lower()
        allowed = (
            "api.coingecko.com",
            "query1.finance.yahoo.com",
            "query2.finance.yahoo.com",
        )
        if host not in allowed:
            return self.json_response(403, {"error": "host not allowed"})

        try:
            raw = fetch_text(target, "application/json, text/plain, */*")
            payload = json.loads(raw)
            return self.json_response(200, payload)
        except Exception as exc:  # noqa: BLE001
            return self.json_response(502, {"error": str(exc)})

    def json_response(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main():
    mimetypes.add_type("text/javascript", ".js")
    HISTORY.mkdir(parents=True, exist_ok=True)
    mt = latest_mtime()
    if mt is not None:
        _scheduler_state["next_run_at"] = mt + BRIEFING_INTERVAL_SEC
    else:
        _scheduler_state["next_run_at"] = time.time()

    threading.Thread(
        target=briefing_scheduler, name="briefing-scheduler", daemon=True
    ).start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"CRYPTO DESK → http://127.0.0.1:{PORT}")
    print("Gemini briefing auto-run: every 8 hours")
    server.serve_forever()


if __name__ == "__main__":
    main()
