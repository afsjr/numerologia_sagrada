"""Vercel serverless endpoint: recebe os dados e devolve o mapa em PDF."""
from __future__ import annotations

import json
import os
import secrets
import tempfile
import urllib.request
from datetime import date
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs

from app import calculate_map, make_pdf


def _value(body: bytes, key: str) -> str:
    values = parse_qs(body.decode("utf-8"), keep_blank_values=True).get(key, [""])
    return values[0].strip()


def _send_webhook(order: dict) -> None:
    webhook = os.environ.get("ORDER_WEBHOOK_URL")
    if not webhook:
        return
    payload = json.dumps(order, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=8):
        pass


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        try:
            name = _value(body, "name")
            email = _value(body, "email")
            birth_date = _value(body, "birth_date")
            target_year = int(_value(body, "target_year") or date.today().year)
            if len(name) < 3 or "@" not in email:
                raise ValueError("Confira nome e e-mail.")
            calculation = calculate_map(name, birth_date, target_year)
            order = {"id": secrets.token_hex(4), "name": name, "email": email, "birth_date": birth_date, "target_year": target_year, "status": "recebido", "calculation": calculation}
            try:
                _send_webhook(order)
            except Exception:
                pass
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf_path = make_pdf({"id": order["id"], "calculation": calculation}, Path(temp_dir))
                encoded = pdf_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", "attachment; filename=mapa-numerologico.pdf")
            self.send_header("X-Order-Id", order["id"])
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except (ValueError, TypeError) as exc:
            message = str(exc).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)

    def do_GET(self):
        message = b"Use POST para gerar um mapa."
        self.send_response(405)
        self.send_header("Allow", "POST")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(message)))
        self.end_headers()
        self.wfile.write(message)
