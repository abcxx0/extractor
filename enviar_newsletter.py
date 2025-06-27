#!/usr/bin/env python3
import argparse, mimetypes, ssl, smtplib, os
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path
import markdown, jinja2, premailer

# ---------- CLI ----------
ap = argparse.ArgumentParser()
ap.add_argument("--md",  default="salida/NEWSLETTER.md",
                help="Markdown de entrada")
ap.add_argument("--tpl", default="plantilla_newsletter.html",
                help="Plantilla HTML Jinja2")
ap.add_argument("--out", default="newsletter_email.html",
                help="HTML de salida")
ap.add_argument("--solo-html", action="store_true",
                help="Solo renderiza el HTML, no envía")
args = ap.parse_args()

# ---------- Cargar markdown y plantilla ----------
md_text  = Path(args.md).read_text(encoding="utf-8")
template = Path(args.tpl).read_text(encoding="utf-8")

cuerpo   = markdown.markdown(md_text, extensions=["tables"])
env      = jinja2.Environment(autoescape=True)
html_raw = env.from_string(template).render(
    asunto      = "📊 Informe semanal 📈",
    titulo      = "📊 Resumen de la semana",
    cuerpo_html = cuerpo,
    enlace_baja = "#"
)

# ---------- Inlinizar CSS ----------
html_ready = premailer.transform(html_raw)

# ---------- Guardar HTML para el workflow ----------
Path(args.out).write_text(html_ready, encoding="utf-8")
print(f"✅ HTML listo en {args.out}")

if args.solo_html:
    exit(0)   # —— FIN para el workflow ——

# ---------- Datos SMTP ----------
SMTP_USER = os.getenv("SMTP_USER")   # tu Gmail desde Secrets
SMTP_PASS = os.getenv("SMTP_PASS")   # App-Password

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465

# ---------- Destinatarios y asunto ----------
TO = ["reimundo.m52@gmail.com"]          # ← destinatario(s) fijo(s)
SUBJECT = "📊 Informe semanal 📈"

# ---------- Construir mensaje ----------
msg = EmailMessage()
msg["Subject"] = SUBJECT
msg["From"]    = SMTP_USER
msg["To"]      = ", ".join(TO)
msg.set_content("Tu cliente no soporta HTML. Abre la versión web.")
msg.add_alternative(html_ready, subtype="html")

# Adjuntar gráficas (CID)
for img in ["salida/line_views.png", "salida/bar_topics.png"]:
    if not Path(img).exists():
        continue
    cid = make_msgid()[1:-1]
    with open(img, "rb") as f:
        maintype, subtype = mimetypes.guess_type(img)[0].split("/")
        msg.get_payload()[1].add_related(
            f.read(), maintype=maintype, subtype=subtype, cid=f"<{cid}>")
    html_ready = html_ready.replace(os.path.basename(img), f"cid:{cid}")

# Reemplazar alternativa con src actualizados
msg.replace_alternative(html_ready, subtype="html")

# ---------- Enviar ----------
ctx = ssl.create_default_context()
with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as s:
    s.login(SMTP_USER, SMTP_PASS)
    s.send_message(msg)
print("📨 Correo enviado 🚀")
