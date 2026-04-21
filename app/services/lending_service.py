import json
import urllib.request
import urllib.error
import ssl

from app.recursos.utils import Environment


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class LendingService:

    @staticmethod
    def authenticate() -> str | None:
        url_auth = Environment.get("auth_base_url")
        url = f"{url_auth}/api/v1/account/login"
        data_auth = Environment.get("lending_credentials")
        payload = json.dumps(data_auth).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, context=_ssl_ctx()) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["data"].get("jwToken")
        except Exception as e:
            print(f"[LendingService] Error autenticando: {e}")
            return None

    @staticmethod
    def get_payments_summary(identity_number: str, token: str) -> dict | None:
        lending_base_url = Environment.get("lending_base_url")
        url = f"{lending_base_url}/api/v1/bot/payments/summary?documentNumber={identity_number}"
        req = urllib.request.Request(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, context=_ssl_ctx()) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"[LendingService] Error consultando pagos: HTTP {e.code} - {e.reason}")
            print(f"[LendingService] Respuesta: {e.read().decode('utf-8')}")
            return None
        except Exception as e:
            print(f"[LendingService] Error consultando pagos: {e}")
            return None

    @staticmethod
    def get_application_status(identity_number: str, token: str) -> dict | None:
        lending_base_url = Environment.get("lending_base_url")
        url = f"{lending_base_url}/api/v1/bot/applications/status/{identity_number}"
        req = urllib.request.Request(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, context=_ssl_ctx()) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"[LendingService] Error consultando solicitudes: HTTP {e.code} - {e.reason}")
            print(f"[LendingService] Respuesta: {e.read().decode('utf-8')}")
            return None
        except Exception as e:
            print(f"[LendingService] Error consultando solicitudes: {e}")
            return None

    @staticmethod
    def get_loan_summary(loan_number: str, token: str) -> dict | None:
        """
        Consulta el resumen general de un préstamo por su número.
        """
        lending_base_url = Environment.get("lending_base_url")
        url = f"{lending_base_url}/api/v1/bot/loans/{loan_number}"
        req = urllib.request.Request(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, context=_ssl_ctx()) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"[LendingService] Error consultando préstamo: HTTP {e.code} - {e.reason}")
            print(f"[LendingService] Respuesta: {e.read().decode('utf-8')}")
            return None
        except Exception as e:
            print(f"[LendingService] Error consultando préstamo: {e}")
            return None

    # ── Formateadores ─────────────────────────────────────────────────────────

    @staticmethod
    def format_payments_message(data: dict) -> str:
        lines = []

        urgent = data["data"].get("urgentPayment")
        if urgent and urgent.get("loanNumber"):
            days = urgent.get("daysUntilDue", 0)
            due_date = urgent.get("dueTime", "N/D")
            total = urgent.get("totalAmountToPay", 0)
            installment = urgent.get("installmentAmount", 0)
            late_fee = urgent.get("lateFeeAmount", 0)

            if days == 0:
                urgency_text = "⚠️ ¡Su pago vence HOY!"
            elif days < 0:
                urgency_text = f"🔴 ¡Su pago está VENCIDO hace {abs(days)} día(s)!"
            else:
                urgency_text = f"🔔 Su próximo pago vence en {days} día(s)"

            lines.append(urgency_text)
            lines.append(f"📋 Préstamo #{urgent['loanNumber']}")
            lines.append(f"   📅 Fecha de vencimiento: {due_date}")
            lines.append(f"   💰 Cuota: RD$ {installment:,.2f}")
            if late_fee and late_fee > 0:
                lines.append(f"   ⚡ Recargo por mora: RD$ {late_fee:,.2f}")
            lines.append(f"   💵 Total a pagar: RD$ {total:,.2f}")

        other_loans = data["data"].get("otherActiveLoans", [])
        active = [l for l in other_loans if l.get("loanNumber")]
        if active:
            lines.append("")
            lines.append(f"📂 Otros préstamos activos ({len(active)}):")
            for loan in active:
                days = loan.get("daysUntilDue", 0)
                due_date = loan.get("dueTime", "N/D")
                total = loan.get("totalAmountToPay", 0)
                late_fee = loan.get("lateFeeAmount", 0)
                status_icon = "🔴" if days < 0 else ("🟡" if days <= 5 else "🟢")
                mora_str = f" (mora: RD$ {late_fee:,.2f})" if late_fee and late_fee > 0 else ""
                lines.append(
                    f"  {status_icon} Préstamo #{loan['loanNumber']} — Vence: {due_date} — Total: RD$ {total:,.2f}{mora_str}"
                )

        if not lines:
            return "✅ No encontré préstamos activos asociados a su documento de identidad."

        return "\n".join(lines)

    @staticmethod
    def format_application_status_message(data: dict) -> str:
        applications = data.get("data", [])

        if not applications:
            return "✅ No encontré solicitudes recientes asociadas a su documento de identidad."

        STATUS_ICONS = {
            "aprobada":    "✅",
            "rechazada":   "❌",
            "pendiente":   "⏳",
            "en revisión": "🔍",
            "cancelada":   "🚫",
        }

        resumen: dict[str, int] = {}
        for app in applications:
            estado = app.get("statusName", "Desconocido")
            resumen[estado] = resumen.get(estado, 0) + 1

        lines = [f"📋 Encontré {len(applications)} solicitud(es) reciente(s):\n"]

        resumen_parts = []
        for estado, cantidad in resumen.items():
            icon = STATUS_ICONS.get(estado.lower(), "📌")
            resumen_parts.append(f"{icon} {cantidad} {estado}(s)")
        lines.append("Resumen: " + " | ".join(resumen_parts))
        lines.append("")

        MAX_DETALLE = 5
        for app in applications[:MAX_DETALLE]:
            codigo = app.get("applicationCode", "N/D")
            monto = app.get("requestedAmount", 0)
            estado = app.get("statusName", "N/D")
            fecha = app.get("lastUpdateDate", "N/D")
            icon = STATUS_ICONS.get(estado.lower(), "📌")
            lines.append(
                f"{icon} {codigo}\n"
                f"   Monto solicitado: RD$ {monto:,.2f}\n"
                f"   Estado: {estado}\n"
                f"   Última actualización: {fecha}"
            )

        if len(applications) > MAX_DETALLE:
            restantes = len(applications) - MAX_DETALLE
            lines.append(f"\n...y {restantes} solicitud(es) más.")

        return "\n".join(lines)

    @staticmethod
    def format_loan_summary_message(data: dict) -> str:
        """
        Convierte el resumen de un préstamo en un mensaje amigable en español.
        """
        loan = data.get("data")

        if not loan:
            return "⚠️ No encontré información para ese número de préstamo."

        loan_number   = loan.get("loanNumber", "N/D")
        status        = loan.get("statusName", "N/D")
        original      = loan.get("originalAmount", 0)
        balance       = loan.get("currentBalance", 0)
        next_date     = loan.get("nextPaymentDate", "N/D")
        next_amount   = loan.get("nextPaymentAmount", 0)

        # Ícono según estado
        STATUS_ICONS = {
            "activo":    "🟢",
            "vencido":   "🔴",
            "pagado":    "✅",
            "cancelado": "🚫",
            "mora":      "⚠️",
        }
        status_icon = STATUS_ICONS.get(status.lower(), "📋")

        # Porcentaje pagado
        pagado = original - balance
        pct = (pagado / original * 100) if original > 0 else 0
        barra = _progress_bar(pct)

        lines = [
            f"🏦 Resumen del Préstamo #{loan_number}",
            "",
            f"{status_icon} Estado: {status}",
            f"💵 Monto original:   RD$ {original:,.2f}",
            f"📉 Saldo actual:     RD$ {balance:,.2f}",
            f"✔️  Monto pagado:    RD$ {pagado:,.2f}",
            f"📊 Progreso: {barra} {pct:.1f}%",
            "",
            f"📅 Próximo pago: {next_date}",
            f"💳 Monto a pagar: RD$ {next_amount:,.2f}",
        ]

        return "\n".join(lines)


def _progress_bar(pct: float, length: int = 10) -> str:
    """Genera una barra de progreso simple con bloques Unicode."""
    filled = round(pct / 100 * length)
    return "█" * filled + "░" * (length - filled)