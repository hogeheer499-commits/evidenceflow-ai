from __future__ import annotations

import hmac
import html
import ipaddress
import json
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .audit import AuditLog
from .persistence import DirectoryPublisher, SQLiteRepository
from .providers import KeywordProvider
from .workflow import EvidenceWorkflow, WorkflowError


def case_summaries(repository: SQLiteRepository) -> list[dict[str, object]]:
    return [
        {
            "case_id": record.case.case_id,
            "title": record.case.title,
            "state": record.state.value,
            "risk": record.assessment.risk.value if record.assessment else None,
            "confidence": (record.assessment.confidence if record.assessment else None),
            "reviewer": record.reviewer,
            "receipt": record.receipt,
        }
        for record in repository.list_records()
    ]


def render_dashboard(
    cases: list[dict[str, object]], *, audit_valid: bool, csrf_token: str
) -> str:
    cards = "".join(_case_card(case, csrf_token) for case in cases)
    if not cards:
        cards = '<p class="empty">No assurance cases have been created yet.</p>'
    audit_label = "Verified" if audit_valid else "Verification failed"
    audit_class = "ok" if audit_valid else "bad"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Kleine Koe EvidenceFlow</title>
  <style>
    :root{{--bg:#fff;--soft:#f5f5f7;--ink:#1d1d1f;--muted:#6e6e73;
      --blue:#0a7cff;--green:#03805c;--red:#b42318;--line:#d2d2d7}}
    *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
    header{{border-bottom:1px solid var(--line);padding:18px 24px}}
    .brand{{max-width:1050px;margin:auto;display:flex;align-items:center;gap:12px}}
    .mark{{width:28px;height:34px;border-radius:55% 45% 48% 52%;background:#111820;
      position:relative}} .mark:after{{content:"";position:absolute;width:8px;
      height:8px;
      border-radius:50%;background:#fff;right:5px;top:7px}}
    .brand strong{{font-size:18px}} .brand span{{color:var(--muted);font-size:14px}}
    main{{max-width:1050px;margin:auto;padding:64px 24px}}
    h1{{font-size:clamp(36px,6vw,64px);letter-spacing:-.04em;margin:0;line-height:1}}
    .lead{{font-size:21px;color:var(--muted);max-width:720px;line-height:1.45}}
    .status{{display:inline-flex;gap:8px;align-items:center;background:var(--soft);
      border-radius:999px;padding:8px 12px;margin:20px 0 38px}}
    .dot{{width:9px;height:9px;border-radius:50%;background:var(--green)}}
    .bad .dot{{background:var(--red)}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}}
    article{{background:var(--soft);border-radius:22px;padding:24px}}
    .eyebrow{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;
      color:var(--muted)}} h2{{font-size:25px;margin:10px 0}}
    .meta{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:18px 0}}
    .metric{{background:#fff;border-radius:13px;padding:13px}}
    .metric small{{display:block;color:var(--muted)}}
    form{{display:flex;gap:9px;flex-wrap:wrap;margin-top:12px}}
    input{{min-width:210px;flex:1;border:1px solid var(--line);border-radius:999px;
      background:#fff;padding:11px 14px}} button{{border:0;border-radius:999px;
      background:var(--blue);color:#fff;padding:11px 17px;cursor:pointer}}
    button.secondary{{background:#111820}} code{{font-size:11px;word-break:break-all}}
    .empty{{padding:40px;background:var(--soft);border-radius:22px}}
    footer{{color:var(--muted);font-size:13px;margin-top:48px}}
  </style>
</head>
<body>
  <header><div class="brand"><i class="mark" aria-hidden="true"></i>
    <div><strong>Kleine Koe</strong><br>
      <span>EvidenceFlow · Sovereign OSS Assurance</span></div>
  </div></header>
  <main>
    <p class="eyebrow">Private AI · Human approval · Traceable evidence</p>
    <h1>Evidence before automation.</h1>
    <p class="lead">Review locally processed scanner evidence. Nothing is exported
      until a named reviewer approves the case.</p>
    <div class="status {audit_class}"><span class="dot"></span>
      Audit chain: {audit_label}</div>
    <div class="grid">{cards}</div>
    <footer>Local pilot console · Bind to loopback only · kleinekoe.nl</footer>
  </main>
</body>
</html>"""


def _case_card(case: dict[str, object], csrf_token: str) -> str:
    escaped_id = html.escape(str(case["case_id"]), quote=True)
    state = html.escape(str(case["state"]))
    risk = html.escape(str(case.get("risk") or "not assessed"))
    reviewer = html.escape(str(case.get("reviewer") or "Not assigned"))
    actions = ""
    if case["state"] == "pending_approval":
        actions = f"""
        <form method="post" action="/approve">
          <input type="hidden" name="csrf" value="{csrf_token}">
          <input type="hidden" name="case_id" value="{escaped_id}">
          <input name="reviewer" maxlength="200" required
            placeholder="reviewer@kleinekoe.nl" aria-label="Named reviewer">
          <button type="submit">Approve</button>
        </form>"""
    elif case["state"] == "approved":
        actions = f"""
        <form method="post" action="/publish">
          <input type="hidden" name="csrf" value="{csrf_token}">
          <input type="hidden" name="case_id" value="{escaped_id}">
          <button class="secondary" type="submit">Create approved export</button>
        </form>"""
    return f"""<article>
      <p class="eyebrow">{state}</p>
      <h2>{html.escape(str(case["title"]))}</h2>
      <code>{escaped_id}</code>
      <div class="meta">
        <div class="metric"><small>Risk</small><strong>{risk}</strong></div>
        <div class="metric"><small>Reviewer</small><strong>{reviewer}</strong></div>
      </div>{actions}
    </article>"""


def serve_dashboard(
    *,
    host: str,
    port: int,
    state_db: Path,
    audit_path: Path,
    approved_dir: Path,
) -> None:
    try:
        if not ipaddress.ip_address(host).is_loopback:
            raise ValueError("dashboard must bind to a loopback address")
    except ValueError as exc:
        raise ValueError("dashboard host must be a loopback IP address") from exc
    repository = SQLiteRepository(state_db)
    audit = AuditLog(audit_path)
    publisher = DirectoryPublisher(approved_dir)
    csrf_token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = "KleineKoeEvidenceFlow/0.2"
        sys_version = ""

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/healthz":
                self._json({"ok": True, "audit_valid": audit.verify()})
                return
            if path == "/api/cases":
                self._json({"cases": case_summaries(repository)})
                return
            if path != "/":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = render_dashboard(
                case_summaries(repository),
                audit_valid=audit.verify(),
                csrf_token=csrf_token,
            ).encode()
            self._send(HTTPStatus.OK, "text/html; charset=utf-8", body)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path not in {"/approve", "/publish"}:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 8192:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            supplied_token = form.get("csrf", [""])[0]
            if not hmac.compare_digest(supplied_token, csrf_token):
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            case_id = form.get("case_id", [""])[0]
            if not case_id or len(case_id) > 512:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            workflow = EvidenceWorkflow(KeywordProvider(), repository, audit)
            try:
                if path == "/approve":
                    reviewer = form.get("reviewer", [""])[0]
                    if not reviewer.strip() or len(reviewer) > 200:
                        self.send_error(HTTPStatus.BAD_REQUEST)
                        return
                    workflow.approve(case_id, reviewer)
                else:
                    workflow.publish(case_id, publisher)
            except WorkflowError as exc:
                self.send_error(HTTPStatus.CONFLICT, str(exc))
                return
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", "/")
            self._security_headers()
            self.end_headers()

        def _json(self, payload: dict[str, object]) -> None:
            self._send(
                HTTPStatus.OK,
                "application/json",
                (json.dumps(payload, default=str) + "\n").encode(),
            )

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self._security_headers()
            self.end_headers()
            self.wfile.write(body)

        def _security_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; "
                "form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
            )

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Kleine Koe EvidenceFlow listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
