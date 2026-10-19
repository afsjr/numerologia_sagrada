#!/usr/bin/env python3
"""Pequena aplicação web sem dependências externas para vender mapas numerológicos.

O servidor usa apenas a biblioteca padrão do Python; o PDF usa ReportLab, já presente
no ambiente. Em produção, trocar o armazenamento e as integrações por serviços seguros.
"""
from __future__ import annotations

import html
import json
import os
import re
import secrets
import threading
import unicodedata
from datetime import date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PDF_DIR = DATA_DIR / "pdfs"
ORDERS_FILE = DATA_DIR / "orders.json"
INDEX_FILE = ROOT / "index.html"
STYLE_FILE = ROOT / "style.css"
ADMIN_KEY = os.environ.get("MAPA_ADMIN_KEY", "demo-admin")
LOCK = threading.Lock()

LETTER_VALUES = {
    **{c: 1 for c in "AIJQY"},
    **{c: 2 for c in "BKR"},
    **{c: 3 for c in "CGLS"},
    **{c: 4 for c in "DMT"},
    **{c: 5 for c in "EHNX"},
    **{c: 6 for c in "UVW"},
    **{c: 7 for c in "OZ"},
    **{c: 8 for c in "FP"},
}
VOWELS = set("AEIOU")
VALID_STATUSES = ("recebido", "pago", "em análise", "aprovado", "entregue")


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).upper()


def reduce_number(value: int, preserve_master: bool = True) -> int:
    while value > 9 and not (preserve_master and value in (11, 22)):
        value = sum(int(digit) for digit in str(value))
    return value


def sum_letters(name: str, predicate=None) -> int:
    letters = normalize_name(name)
    return sum(LETTER_VALUES.get(ch, 0) for ch in letters if ch.isalpha() and (predicate is None or predicate(ch)))


def calculate_map(name: str, birth_date: str, target_year: int) -> dict:
    clean = " ".join((name or "").strip().split())
    parsed = datetime.strptime(birth_date, "%Y-%m-%d").date()
    normalized = normalize_name(clean)
    vowels_sum = sum_letters(clean, lambda ch: ch in VOWELS)
    consonants_sum = sum_letters(clean, lambda ch: ch.isalpha() and ch not in VOWELS)
    expression_sum = sum_letters(clean)
    day = parsed.day
    destiny_sum = parsed.day + parsed.month + parsed.year
    personal_sum = parsed.day + parsed.month + target_year
    year_universal_sum = sum(int(d) for d in str(target_year))
    mission_sum = reduce_number(expression_sum) + reduce_number(destiny_sum)
    occurrences = {n: sum(1 for ch in normalized if LETTER_VALUES.get(ch) == n) for n in range(1, 9)}
    hidden = max(occurrences, key=occurrences.get) if any(occurrences.values()) else None
    missing = [n for n in range(1, 9) if occurrences[n] == 0]
    return {
        "name": clean,
        "birth_date": parsed.strftime("%d/%m/%Y"),
        "target_year": target_year,
        "motivation": {"sum": vowels_sum, "result": reduce_number(vowels_sum)},
        "impression": {"sum": consonants_sum, "result": reduce_number(consonants_sum)},
        "expression": {"sum": expression_sum, "result": reduce_number(expression_sum)},
        "destiny": {"sum": destiny_sum, "result": reduce_number(destiny_sum)},
        "birth_day": {"sum": day, "result": reduce_number(day)},
        "psychic": {"sum": day, "result": reduce_number(day)},
        "mission": {"sum": mission_sum, "result": reduce_number(mission_sum)},
        "universal_year": {"sum": year_universal_sum, "result": reduce_number(year_universal_sum)},
        "personal_year": {"sum": personal_sum, "result": reduce_number(personal_sum)},
        "personal_months": [reduce_number(reduce_number(personal_sum) + month) for month in range(1, 13)],
        "hidden_tendency": hidden,
        "karmic_lesson": missing[0] if missing else None,
        "unsupported": ["Dívida Cármica", "Resposta Subconsciente", "Triângulo da Vida completo"],
    }


def load_orders() -> list[dict]:
    if not ORDERS_FILE.exists():
        return []
    try:
        return json.loads(ORDERS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_orders(orders: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    ORDERS_FILE.write_text(json.dumps(orders, ensure_ascii=False, indent=2), encoding="utf-8")


def make_pdf(order: dict) -> Path:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    path = PDF_DIR / f"mapa-{order['id']}.pdf"
    result = order["calculation"]
    styles = getSampleStyleSheet()
    title = ParagraphStyle("Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=21, leading=25, alignment=TA_CENTER, textColor=HexColor("#1d2938"), spaceAfter=8)
    subtitle = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=11, leading=15, alignment=TA_CENTER, textColor=HexColor("#765d73"), spaceAfter=22)
    heading = ParagraphStyle("Heading", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=HexColor("#5f3d5c"), spaceBefore=14, spaceAfter=7)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9.5, leading=14, textColor=HexColor("#29323d"), spaceAfter=7)
    quote = ParagraphStyle("Quote", parent=body, fontSize=11, leading=15, leftIndent=14, rightIndent=14, textColor=HexColor("#315d61"), spaceBefore=5, spaceAfter=12)

    def p(value, style=body):
        return Paragraph(escape(str(value)).replace("\n", "<br/>") , style)

    story = [Spacer(1, 1.2 * cm), Paragraph("MAPA NUMEROLÓGICO", title), Paragraph(html.escape(result["name"]), subtitle)]
    story += [p(f"Data de nascimento: {result['birth_date']}"), p(f"Ano analisado: {result['target_year']}"), p("Leitura simbólica para autoconhecimento")]
    story += [Paragraph("Uma leitura para voltar ao centro", heading), p("Este mapa organiza símbolos numerológicos como convite à reflexão. Ele não determina acontecimentos: oferece perguntas, padrões e possibilidades para que você escolha seus próprios caminhos.")]
    story += [Paragraph("Síntese do mapa", heading), p(f"Sua combinação principal reúne Motivação {result['motivation']['result']}, Expressão {result['expression']['result']}, Impressão {result['impression']['result']} e Destino {result['destiny']['result']}. Ela sugere uma pessoa com desejos internos, talentos visíveis e aprendizados relacionais que podem ser integrados com mais consciência.")]
    story += [Paragraph("Cálculos principais", heading)]
    rows = [["Elemento", "Soma", "Resultado"], ["Motivação", result["motivation"]["sum"], result["motivation"]["result"]], ["Impressão", result["impression"]["sum"], result["impression"]["result"]], ["Expressão", result["expression"]["sum"], result["expression"]["result"]], ["Destino", result["destiny"]["sum"], result["destiny"]["result"]], ["Dia natalício", result["birth_day"]["sum"], result["birth_day"]["result"]], ["Missão", result["mission"]["sum"], result["mission"]["result"]], [f"Ano pessoal {result['target_year']}", result["personal_year"]["sum"], result["personal_year"]["result"]]]
    table = Table(rows, colWidths=[7.5 * cm, 4 * cm, 4 * cm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), HexColor("#5f3d5c")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .25, HexColor("#c7d1d4")), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#f3eee9")]), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(table)
    story += [Paragraph("Integração e prática", heading), p(f"O número de Motivação {result['motivation']['result']} fala do impulso interno; a Expressão {result['expression']['result']} mostra como seus talentos podem ganhar forma; a Impressão {result['impression']['result']} descreve a primeira imagem que você transmite; e o Destino {result['destiny']['result']} aponta aprendizados por meio das experiências.")]
    story += [p("Escolha uma pergunta para os próximos dias: onde estou buscando liberdade, onde preciso de estrutura e qual decisão pode ser tomada com mais autoria? Anote percepções, fatos e próximos passos antes de agir.")]
    story += [Paragraph("Meses pessoais", heading), p(" ".join(f"{n + 1}: {value}" for n, value in enumerate(result["personal_months"]))) ]
    story += [Paragraph("Limites da leitura", heading), p("A numerologia é uma linguagem simbólica de autoconhecimento. Não substitui profissionais de saúde, psicologia, direito ou finanças, nem determina o futuro. Você mantém autonomia para decidir os rumos da própria vida. Que este mapa seja uma porta: você é quem atravessa.")]
    def footer(canvas, doc):
        canvas.saveState(); canvas.setFont("Helvetica", 7.5); canvas.setFillColor(HexColor("#765d73")); canvas.drawString(1.7 * cm, 1.1 * cm, "Autoconhecimento • leitura numerológica"); canvas.drawRightString(A4[0] - 1.7 * cm, 1.1 * cm, f"Página {doc.page}"); canvas.restoreState()
    SimpleDocTemplate(str(path), pagesize=A4, rightMargin=1.7 * cm, leftMargin=1.7 * cm, topMargin=1.6 * cm, bottomMargin=1.8 * cm, title=f"Mapa Numerológico - {result['name']}").build(story, onFirstPage=footer, onLaterPages=footer)
    return path


def render_page(message: str = "") -> bytes:
    page = INDEX_FILE.read_text(encoding="utf-8")
    page = page.replace("{{MESSAGE}}", html.escape(message))
    return page.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "AuroraNumerologica/1.0"

    def log_message(self, fmt, *args):
        return

    def send_bytes(self, payload: bytes, content_type: str, status=HTTPStatus.OK):
        self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)

    def send_text(self, message: str, status=HTTPStatus.OK):
        self.send_bytes(message.encode("utf-8"), "text/html; charset=utf-8", status)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self.send_bytes(render_page(), "text/html; charset=utf-8"); return
        if parsed.path == "/style.css":
            self.send_bytes(STYLE_FILE.read_bytes(), "text/css; charset=utf-8"); return
        if parsed.path == "/admin":
            key = parse_qs(parsed.query).get("key", [""])[0]
            if key != ADMIN_KEY:
                self.send_text("Acesso reservado. Use /admin?key=...", HTTPStatus.UNAUTHORIZED); return
            rows = []
            for order in load_orders():
                rows.append(f"<tr><td>{html.escape(order['id'])}</td><td>{html.escape(order['name'])}</td><td>{html.escape(order['email'])}</td><td>{html.escape(order['status'])}</td><td><a href='/admin/{order['id']}?key={html.escape(key)}'>abrir</a></td></tr>")
            body = "<h1>Pedidos</h1><table><tr><th>ID</th><th>Nome</th><th>E-mail</th><th>Status</th><th>Ação</th></tr>" + "".join(rows) + "</table>"
            self.send_text(f"<link rel='stylesheet' href='/style.css'><main class='admin'>{body}</main>"); return
        if parsed.path.startswith("/download/"):
            order_id = parsed.path.rsplit("/", 1)[-1]
            order = next((o for o in load_orders() if o["id"] == order_id), None)
            if not order or order.get("status") not in ("aprovado", "entregue"):
                self.send_text("Relatório ainda não disponível.", HTTPStatus.NOT_FOUND); return
            path = PDF_DIR / f"mapa-{order_id}.pdf"
            if not path.exists():
                make_pdf(order)
            data = path.read_bytes(); self.send_response(200); self.send_header("Content-Type", "application/pdf"); self.send_header("Content-Disposition", f"attachment; filename=mapa-{order_id}.pdf"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
        if parsed.path.startswith("/admin/"):
            key = parse_qs(parsed.query).get("key", [""])[0]
            if key != ADMIN_KEY: self.send_text("Acesso reservado.", HTTPStatus.UNAUTHORIZED); return
            order_id = parsed.path.rsplit("/", 1)[-1]; order = next((o for o in load_orders() if o["id"] == order_id), None)
            if not order: self.send_text("Pedido não encontrado.", HTTPStatus.NOT_FOUND); return
            options = "".join(f"<option {'selected' if order['status']==s else ''}>{s}</option>" for s in VALID_STATUSES)
            content = f"<h1>Revisar pedido {html.escape(order_id)}</h1><p><strong>{html.escape(order['name'])}</strong> · {html.escape(order['email'])}</p><pre>{html.escape(json.dumps(order['calculation'], ensure_ascii=False, indent=2))}</pre><form method='post'><input type='hidden' name='key' value='{html.escape(key)}'><label>Status<select name='status'>{options}</select></label><label>Observação<textarea name='note'>{html.escape(order.get('note',''))}</textarea></label><button>Salvar revisão</button></form><p><a href='/admin?key={html.escape(key)}'>Voltar</a></p>"
            self.send_text(f"<link rel='stylesheet' href='/style.css'><main class='admin'>{content}</main>"); return
        self.send_text("Não encontrado.", HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urlparse(self.path); length = int(self.headers.get("Content-Length", 0)); raw = self.rfile.read(length).decode("utf-8"); data = {k: v[0] for k, v in parse_qs(raw).items()}
        if parsed.path == "/orders":
            try:
                name, email, birth_date = data.get("name", "").strip(), data.get("email", "").strip(), data.get("birth_date", "")
                target_year = int(data.get("target_year", date.today().year))
                if len(name) < 3 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email): raise ValueError("Confira nome e e-mail.")
                calculation = calculate_map(name, birth_date, target_year)
            except (ValueError, TypeError) as exc:
                self.send_bytes(render_page(f"Não foi possível criar o pedido: {exc}"), "text/html; charset=utf-8", HTTPStatus.BAD_REQUEST); return
            order = {"id": secrets.token_hex(4), "name": name, "email": email, "birth_date": birth_date, "target_year": target_year, "status": "recebido", "created_at": datetime.now().isoformat(timespec="seconds"), "calculation": calculation, "note": ""}
            with LOCK:
                orders = load_orders(); orders.append(order); save_orders(orders)
            self.send_bytes(render_page(f"Pedido {order['id']} recebido. A especialista fará a revisão antes da entrega."), "text/html; charset=utf-8"); return
        if parsed.path.startswith("/admin/"):
            key = data.get("key", "")
            if key != ADMIN_KEY: self.send_text("Acesso reservado.", HTTPStatus.UNAUTHORIZED); return
            order_id = parsed.path.rsplit("/", 1)[-1]
            with LOCK:
                orders = load_orders(); order = next((o for o in orders if o["id"] == order_id), None)
                if not order: self.send_text("Pedido não encontrado.", HTTPStatus.NOT_FOUND); return
                if data.get("status") in VALID_STATUSES: order["status"] = data["status"]
                order["note"] = data.get("note", ""); order["updated_at"] = datetime.now().isoformat(timespec="seconds"); save_orders(orders)
                if order["status"] in ("aprovado", "entregue"): make_pdf(order)
            self.send_text(f"<link rel='stylesheet' href='/style.css'><main class='admin'><p>Pedido atualizado.</p><a href='/admin/{order_id}?key={html.escape(key)}'>voltar</a></main>"); return
        self.send_text("Não encontrado.", HTTPStatus.NOT_FOUND)


def main():
    port = int(os.environ.get("PORT", "8000")); server = ThreadingHTTPServer(("127.0.0.1", port), Handler); print(f"Site disponível em http://127.0.0.1:{port}"); server.serve_forever()


if __name__ == "__main__":
    main()
