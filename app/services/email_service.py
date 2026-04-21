"""
EmailService — Envío de correos con smtplib (sin dependencias externas)
-----------------------------------------------------------------------
Configura las variables SMTP en Environment (utils.py):
    "smtp_host"     → ej. "smtp.gmail.com"
    "smtp_port"     → ej. 587
    "smtp_user"     → ej. "bot@tudominio.com"
    "smtp_password" → contraseña o app-password
    "smtp_from"     → remitente visible, ej. "Credio Bot <bot@tudominio.com>"
"""

import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.recursos.utils import Environment

# Regex simple pero suficiente para validar e-mails
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def validate_email(address: str) -> bool:
    """Devuelve True si el string tiene formato de correo válido."""
    return bool(_EMAIL_RE.match(address.strip()))


class EmailService:

    @staticmethod
    def send_application_status(to_email: str, identity_number: str, data: dict) -> bool:
        """
        Envía al correo `to_email` el reporte completo de solicitudes.
        Devuelve True si el envío fue exitoso, False en caso contrario.
        """
        host     = Environment.get("smtp_host", "smtp.gmail.com")
        port     = int(Environment.get("smtp_port", 587))
        user     = Environment.get("smtp_user", "")
        password = Environment.get("smtp_password", "")
        from_addr = Environment.get("smtp_from", user)

        subject = f"Estado de tus solicitudes — Credio SGCC (Doc: {identity_number})"
        html_body = EmailService._build_html(identity_number, data)
        plain_body = EmailService._build_plain(identity_number, data)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = from_addr
        msg["To"]      = to_email
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body,  "html",  "utf-8"))

        try:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.login(user, password)
                server.sendmail(from_addr, [to_email], msg.as_string())
            return True
        except Exception as e:
            print(f"[EmailService] Error enviando correo: {e}")
            return False

    # ── Builders ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_plain(identity_number: str, data: dict) -> str:
        applications = data.get("data", [])
        lines = [
            "ESTADO DE SOLICITUDES — CREDIO SGCC",
            f"Documento: {identity_number}",
            f"Total de solicitudes: {len(applications)}",
            "=" * 40,
            "",
        ]
        for i, app in enumerate(applications, 1):
            lines += [
                f"Solicitud #{i}",
                f"  Código:               {app.get('applicationCode', 'N/D')}",
                f"  Monto solicitado:     RD$ {app.get('requestedAmount', 0):,.2f}",
                f"  Estado:               {app.get('statusName', 'N/D')}",
                f"  Última actualización: {app.get('lastUpdateDate', 'N/D')}",
                "",
            ]
        lines.append("Este mensaje fue generado automáticamente por el asistente virtual SGCC.")
        return "\n".join(lines)

    @staticmethod
    def _build_html(identity_number: str, data: dict) -> str:
        applications = data.get("data", [])

        STATUS_COLORS = {
            "aprobada":    ("#d4edda", "#155724"),
            "rechazada":   ("#f8d7da", "#721c24"),
            "pendiente":   ("#fff3cd", "#856404"),
            "en revisión": ("#d1ecf1", "#0c5460"),
            "cancelada":   ("#e2e3e5", "#383d41"),
        }
        DEFAULT_COLOR = ("#f0f0f0", "#333333")

        rows = ""
        for app in applications:
            estado     = app.get("statusName", "N/D")
            bg, fg     = STATUS_COLORS.get(estado.lower(), DEFAULT_COLOR)
            codigo     = app.get("applicationCode", "N/D")
            monto      = app.get("requestedAmount", 0)
            fecha      = app.get("lastUpdateDate", "N/D")
            rows += f"""
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #dee2e6;">{codigo}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #dee2e6;">RD$ {monto:,.2f}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #dee2e6;">
                    <span style="background:{bg};color:{fg};padding:3px 8px;border-radius:4px;font-size:13px;">
                        {estado}
                    </span>
                </td>
                <td style="padding:8px 12px;border-bottom:1px solid #dee2e6;">{fecha}</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Estado de Solicitudes</title></head>
<body style="font-family:Arial,sans-serif;background:#f4f6f9;margin:0;padding:20px;">
  <div style="max-width:680px;margin:auto;background:#fff;border-radius:8px;
              box-shadow:0 2px 8px rgba(0,0,0,.1);overflow:hidden;">

    <!-- Header -->
    <div style="background:#1a3c5e;padding:24px 28px;">
      <h1 style="color:#fff;margin:0;font-size:22px;">📋 Estado de tus Solicitudes</h1>
      <p style="color:#a8c4de;margin:6px 0 0;">
        Sistema Integral de Gestión de Créditos y Cobranza — SGCC
      </p>
    </div>

    <!-- Summary bar -->
    <div style="background:#eef2f7;padding:14px 28px;border-bottom:1px solid #dee2e6;">
      <strong>Documento:</strong> {identity_number} &nbsp;|&nbsp;
      <strong>Total de solicitudes:</strong> {len(applications)}
    </div>

    <!-- Table -->
    <div style="padding:24px 28px;">
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
          <tr style="background:#f0f4f8;">
            <th style="text-align:left;padding:10px 12px;border-bottom:2px solid #dee2e6;">Código</th>
            <th style="text-align:left;padding:10px 12px;border-bottom:2px solid #dee2e6;">Monto Solicitado</th>
            <th style="text-align:left;padding:10px 12px;border-bottom:2px solid #dee2e6;">Estado</th>
            <th style="text-align:left;padding:10px 12px;border-bottom:2px solid #dee2e6;">Última Actualización</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>

    <!-- Footer -->
    <div style="background:#f4f6f9;padding:16px 28px;text-align:center;
                font-size:12px;color:#888;border-top:1px solid #dee2e6;">
      Este mensaje fue generado automáticamente por el asistente virtual SGCC.<br>
      Por favor no responda a este correo.
    </div>
  </div>
</body>
</html>"""