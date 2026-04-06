#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import sys
from datetime import datetime
from email.message import EmailMessage
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
import smtplib


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR))).resolve()
DB_PATH = DATA_DIR / "scheduler.db"
INDEX_PATH = BASE_DIR / "index.html"
ADMIN_PATH = BASE_DIR / "admin.html"

ADMIN_PIN = os.environ.get("ADMIN_PIN", "changeme")
SESSIONS: dict[str, dict[str, Any]] = {}

DEFAULT_SLOTS = [
    {
        "slug": "sarabeths-greenwich-0506",
        "event_date": "2026-05-06",
        "event_time": "12:30 PM",
        "venue": "Sarabeth's Greenwich",
        "area": "Greenwich Village",
        "needs": "Needs attorney & lender",
        "sort_order": 1,
    },
    {
        "slug": "green-kitchen-ues-0512",
        "event_date": "2026-05-12",
        "event_time": "10:30 AM",
        "venue": "Green Kitchen UES",
        "area": "Upper East Side",
        "needs": "Needs attorney & lender",
        "sort_order": 2,
    },
    {
        "slug": "bowery-road-0520",
        "event_date": "2026-05-20",
        "event_time": "10:30 AM",
        "venue": "Bowery Road Union Square",
        "area": "Union Square",
        "needs": "Needs attorney & lender",
        "sort_order": 3,
    },
    {
        "slug": "cafe-paulette-0522",
        "event_date": "2026-05-22",
        "event_time": "10:30 AM",
        "venue": "Café Paulette Fort Greene",
        "area": "Fort Greene",
        "needs": "Needs attorney & lender",
        "sort_order": 4,
    },
    {
        "slug": "sarabeths-uws-0526",
        "event_date": "2026-05-26",
        "event_time": "10:30 AM",
        "venue": "Sarabeth's UWS",
        "area": "Upper West Side",
        "needs": "Needs attorney & lender",
        "sort_order": 5,
    },
]


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = db()
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                event_date TEXT NOT NULL,
                event_time TEXT NOT NULL,
                venue TEXT NOT NULL,
                area TEXT,
                needs TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_id INTEGER NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                company_role TEXT,
                attendee_role TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(slot_id) REFERENCES slots(id) ON DELETE CASCADE
            );
            """
        )

        existing = conn.execute("SELECT COUNT(*) AS count FROM slots").fetchone()["count"]
        if existing == 0:
            timestamp = datetime.utcnow().isoformat()
            conn.executemany(
                """
                INSERT INTO slots (slug, event_date, event_time, venue, area, needs, status, sort_order, created_at)
                VALUES (:slug, :event_date, :event_time, :venue, :area, :needs, 'available', :sort_order, :created_at)
                """,
                [{**slot, "created_at": timestamp} for slot in DEFAULT_SLOTS],
            )
    conn.close()


def read_file(path: Path) -> bytes:
    return path.read_bytes()


def row_to_slot(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "slug": row["slug"],
        "date": row["event_date"],
        "time": row["event_time"],
        "venue": row["venue"],
        "area": row["area"],
        "needs": row["needs"],
        "status": row["status"],
        "sortOrder": row["sort_order"],
    }


def list_slots(include_booked: bool = True) -> list[dict[str, Any]]:
    conn = db()
    query = """
        SELECT id, slug, event_date, event_time, venue, area, needs, status, sort_order
        FROM slots
    """
    if not include_booked:
        query += " WHERE status = 'available'"
    query += " ORDER BY event_date, sort_order, id"
    rows = [row_to_slot(row) for row in conn.execute(query).fetchall()]
    conn.close()
    return rows


def list_registrations() -> list[dict[str, Any]]:
    conn = db()
    rows = conn.execute(
        """
        SELECT
            r.id,
            r.full_name,
            r.email,
            r.company_role,
            r.attendee_role,
            r.notes,
            r.created_at,
            s.id AS slot_id,
            s.slug,
            s.event_date,
            s.event_time,
            s.venue,
            s.area,
            s.needs
        FROM registrations r
        JOIN slots s ON s.id = r.slot_id
        ORDER BY s.event_date, s.sort_order, r.created_at DESC
        """
    ).fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "fullName": row["full_name"],
            "email": row["email"],
            "companyRole": row["company_role"] or "",
            "attendeeRole": row["attendee_role"],
            "notes": row["notes"] or "",
            "createdAt": row["created_at"],
            "slot": {
                "id": row["slot_id"],
                "slug": row["slug"],
                "date": row["event_date"],
                "time": row["event_time"],
                "venue": row["venue"],
                "area": row["area"],
                "needs": row["needs"],
            },
        }
        for row in rows
    ]


def organizer_email_enabled() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("ORGANIZER_EMAIL"))


def send_email(subject: str, body: str, to_email: str) -> None:
    host = os.environ.get("SMTP_HOST")
    if not host:
        return
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USERNAME", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    from_email = os.environ.get("FROM_EMAIL", username or "no-reply@example.com")
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() != "false"

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)


def send_sms(body: str) -> None:
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    to_number = os.environ.get("TWILIO_TO_NUMBER")
    from_number = os.environ.get("TWILIO_FROM_NUMBER")
    if not all([account_sid, auth_token, to_number, from_number]):
        return

    payload = parse_qs("")
    payload = f"To={to_number}&From={from_number}&Body={body}".encode()
    request = Request(
        url=f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
        data=payload,
        method="POST",
        headers={
            "Authorization": "Basic " + _basic_auth(account_sid, auth_token),
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urlopen(request, timeout=20):
        return


def _basic_auth(username: str, password: str) -> str:
    import base64
    token = f"{username}:{password}".encode()
    return base64.b64encode(token).decode()


def notify_booking(registration: dict[str, Any]) -> None:
    slot = registration["slot"]
    organizer = os.environ.get("ORGANIZER_EMAIL", "")
    subject = f"New roundtable booking: {slot['venue']} on {slot['date']}"
    body = (
        f"New booking received\n\n"
        f"Name: {registration['fullName']}\n"
        f"Email: {registration['email']}\n"
        f"Company / Role: {registration['companyRole'] or 'Not provided'}\n"
        f"Attending as: {registration['attendeeRole']}\n"
        f"Date: {slot['date']}\n"
        f"Time: {slot['time']}\n"
        f"Venue: {slot['venue']}\n"
        f"Area: {slot['area']}\n"
        f"Needs: {slot['needs']}\n"
        f"Notes: {registration['notes'] or 'None'}\n"
    )

    try:
        if organizer:
            send_email(subject, body, organizer)
    except Exception as exc:
        print(f"Email notification failed: {exc}", file=sys.stderr)

    try:
        sms = (
            f"New booking: {registration['fullName']} | {slot['venue']} | "
            f"{slot['date']} {slot['time']} | {registration['attendeeRole']}"
        )
        send_sms(sms)
    except Exception as exc:
        print(f"SMS notification failed: {exc}", file=sys.stderr)

    if os.environ.get("SEND_USER_CONFIRMATION", "false").lower() == "true":
        try:
            send_email(
                f"Confirmed: {slot['venue']} on {slot['date']}",
                body,
                registration["email"],
            )
        except Exception as exc:
            print(f"User confirmation failed: {exc}", file=sys.stderr)


def create_registration(payload: dict[str, Any]) -> dict[str, Any]:
    required = ["slotId", "fullName", "email", "attendeeRole"]
    for key in required:
        if not payload.get(key):
            raise ValueError(f"Missing field: {key}")

    conn = db()
    try:
        with conn:
            slot = conn.execute(
                "SELECT * FROM slots WHERE id = ?",
                (payload["slotId"],),
            ).fetchone()
            if not slot:
                raise ValueError("Selected slot was not found.")
            if slot["status"] != "available":
                raise ValueError("That slot is no longer available.")

            registration_time = datetime.utcnow().isoformat()
            conn.execute(
                """
                INSERT INTO registrations (slot_id, full_name, email, company_role, attendee_role, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["slotId"],
                    payload["fullName"].strip(),
                    payload["email"].strip(),
                    payload.get("companyRole", "").strip(),
                    payload["attendeeRole"].strip(),
                    payload.get("notes", "").strip(),
                    registration_time,
                ),
            )
            conn.execute("UPDATE slots SET status = 'booked' WHERE id = ?", (payload["slotId"],))

        row = conn.execute(
            """
            SELECT
                r.id,
                r.full_name,
                r.email,
                r.company_role,
                r.attendee_role,
                r.notes,
                r.created_at,
                s.id AS slot_id,
                s.slug,
                s.event_date,
                s.event_time,
                s.venue,
                s.area,
                s.needs
            FROM registrations r
            JOIN slots s ON s.id = r.slot_id
            WHERE r.slot_id = ?
            """,
            (payload["slotId"],),
        ).fetchone()
        result = {
            "id": row["id"],
            "fullName": row["full_name"],
            "email": row["email"],
            "companyRole": row["company_role"] or "",
            "attendeeRole": row["attendee_role"],
            "notes": row["notes"] or "",
            "createdAt": row["created_at"],
            "slot": {
                "id": row["slot_id"],
                "slug": row["slug"],
                "date": row["event_date"],
                "time": row["event_time"],
                "venue": row["venue"],
                "area": row["area"],
                "needs": row["needs"],
            },
        }
        conn.close()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    notify_booking(result)
    return result


def create_slot(payload: dict[str, Any]) -> dict[str, Any]:
    required = ["eventDate", "eventTime", "venue", "needs"]
    for key in required:
        if not payload.get(key):
            raise ValueError(f"Missing field: {key}")

    slug = payload.get("slug") or (
        f"{payload['venue'].lower().replace(' ', '-')}-{payload['eventDate'].replace('-', '')}"
    )

    conn = db()
    with conn:
        conn.execute(
            """
            INSERT INTO slots (slug, event_date, event_time, venue, area, needs, status, sort_order, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                slug,
                payload["eventDate"],
                payload["eventTime"],
                payload["venue"].strip(),
                payload.get("area", "").strip(),
                payload["needs"].strip(),
                payload.get("status", "available"),
                int(payload.get("sortOrder", 0)),
                datetime.utcnow().isoformat(),
            ),
        )
        row = conn.execute("SELECT * FROM slots WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    return row_to_slot(row)


def update_slot(slot_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "event_date": payload.get("eventDate"),
        "event_time": payload.get("eventTime"),
        "venue": payload.get("venue"),
        "area": payload.get("area", ""),
        "needs": payload.get("needs"),
        "status": payload.get("status"),
        "sort_order": payload.get("sortOrder"),
    }
    clean_fields = {k: v for k, v in fields.items() if v is not None}
    if not clean_fields:
        raise ValueError("No slot changes were provided.")

    set_clause = ", ".join(f"{field} = ?" for field in clean_fields)
    values = list(clean_fields.values()) + [slot_id]

    conn = db()
    with conn:
        conn.execute(f"UPDATE slots SET {set_clause} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM slots WHERE id = ?", (slot_id,)).fetchone()
    conn.close()
    if not row:
        raise ValueError("Slot not found.")
    return row_to_slot(row)


def delete_slot(slot_id: int) -> None:
    conn = db()
    with conn:
        conn.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
    conn.close()


class AppHandler(BaseHTTPRequestHandler):
    server_version = "CoverageScheduler/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path

        if route in {"/", "/index.html"}:
            self._serve_file(INDEX_PATH, "text/html; charset=utf-8")
            return
        if route == "/admin" or route == "/admin.html":
            self._serve_file(ADMIN_PATH, "text/html; charset=utf-8")
            return
        if route == "/api/slots":
            self._json({"slots": list_slots(include_booked=True)})
            return
        if route == "/api/admin/slots":
            self._require_admin()
            self._json({"slots": list_slots(include_booked=True)})
            return
        if route == "/api/admin/registrations":
            self._require_admin()
            self._json({"registrations": list_registrations()})
            return
        if route == "/api/admin/session":
            self._json({"authenticated": self._is_admin()})
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        body = self._read_json()

        try:
            if route == "/api/book":
                registration = create_registration(body)
                self._json({"ok": True, "registration": registration}, status=201)
                return
            if route == "/api/admin/login":
                if body.get("pin") != ADMIN_PIN:
                    self._json({"error": "Incorrect admin PIN."}, status=401)
                    return
                token = secrets.token_hex(24)
                SESSIONS[token] = {"createdAt": datetime.utcnow().isoformat()}
                headers = {"Set-Cookie": f"session={token}; HttpOnly; Path=/; SameSite=Lax"}
                self._json({"ok": True}, headers=headers)
                return
            if route == "/api/admin/logout":
                token = self._session_token()
                if token and token in SESSIONS:
                    del SESSIONS[token]
                headers = {"Set-Cookie": "session=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax"}
                self._json({"ok": True}, headers=headers)
                return
            if route == "/api/admin/slots":
                self._require_admin()
                slot = create_slot(body)
                self._json({"ok": True, "slot": slot}, status=201)
                return
        except PermissionError as exc:
            self._json({"error": str(exc)}, status=401)
            return
        except ValueError as exc:
            self._json({"error": str(exc)}, status=400)
            return
        except sqlite3.IntegrityError as exc:
            self._json({"error": f"Database error: {exc}"}, status=400)
            return

        self.send_error(404, "Not Found")

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/admin/slots/"):
            self.send_error(404, "Not Found")
            return

        try:
            self._require_admin()
            slot_id = int(parsed.path.rsplit("/", 1)[-1])
            slot = update_slot(slot_id, self._read_json())
            self._json({"ok": True, "slot": slot})
        except PermissionError as exc:
            self._json({"error": str(exc)}, status=401)
        except ValueError as exc:
            self._json({"error": str(exc)}, status=400)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/admin/slots/"):
            self.send_error(404, "Not Found")
            return

        try:
            self._require_admin()
            slot_id = int(parsed.path.rsplit("/", 1)[-1])
            delete_slot(slot_id)
            self._json({"ok": True})
        except PermissionError as exc:
            self._json({"error": str(exc)}, status=401)
        except ValueError as exc:
            self._json({"error": str(exc)}, status=400)

    def _serve_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404, "File not found")
            return
        content = read_file(path)
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")

    def _json(self, payload: dict[str, Any], status: int = 200, headers: dict[str, str] | None = None) -> None:
        encoded = json.dumps(payload).encode()
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode() if length else "{}"
        return json.loads(raw or "{}")

    def _session_token(self) -> str | None:
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return None
        jar = cookies.SimpleCookie()
        jar.load(cookie_header)
        morsel = jar.get("session")
        return morsel.value if morsel else None

    def _is_admin(self) -> bool:
        token = self._session_token()
        return bool(token and token in SESSIONS)

    def _require_admin(self) -> None:
        if not self._is_admin():
            raise PermissionError("Admin login required.")


def main() -> None:
    init_db()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Coverage Scheduler running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")


if __name__ == "__main__":
    main()
