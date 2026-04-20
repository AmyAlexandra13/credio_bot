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
        """
        Se autentica contra el API de lending y devuelve el jwToken.
        Retorna None si falla.
        """

        url_auth = Environment.get("auth_base_url")

        url = f"{url_auth}/api/v1/account/login"
        # payload = json.dumps(LENDING_CREDENTIALS).encode("utf-8")

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
                return data['data'].get("jwToken")
        except Exception as e:
            print(f"[LendingService] Error autenticando: {e}")
            return None

    @staticmethod
    def get_payments_summary(identity_number: str, token: str) -> dict | None:
        """
        Consulta los próximos pagos por número de identidad.
        Retorna el dict de la respuesta o None si falla.
        """

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
        except Exception as e:
            print(f"[LendingService] Error consultando pagos: {e}")
            print(f"[LendingService] HTTP Error: {e.code} - {e.reason}")
            print(f"[LendingService] Respuesta del servidor: {e.read().decode('utf-8')}")
            return None

    @staticmethod
    def format_payments_message(data: dict) -> str:
        """
        Convierte la respuesta JSON de pagos en un mensaje amigable en español.
        """
        lines = []

        urgent = data['data'].get("urgentPayment")
        if urgent and urgent.get("loanNumber"):
            days = urgent.get("daysUntilDue", 0)
            due_date = urgent.get("dueTime", "N/D")
            total = urgent.get("totalAmountToPay", 0)
            installment = urgent.get("installmentAmount", 0)
            late_fee = urgent.get("lateFeeAmount", 0)

            if days == 0:
                urgency_text = "⚠️ *¡Su pago vence HOY!*"
            elif days < 0:
                urgency_text = f"🔴 *¡Su pago está VENCIDO hace {abs(days)} día(s)!*"
            else:
                urgency_text = f"🔔 *Su próximo pago vence en {days} día(s)*"

            lines.append(urgency_text)
            lines.append(f"📋 *Préstamo #{urgent['loanNumber']}*")
            lines.append(f"   📅 Fecha de vencimiento: {due_date}")
            lines.append(f"   💰 Cuota: RD$ {installment:,.2f}")
            if late_fee and late_fee > 0:
                lines.append(f"   ⚡ Recargo por mora: RD$ {late_fee:,.2f}")
            lines.append(f"   💵 *Total a pagar: RD$ {total:,.2f}*")

        other_loans = data['data'].get("otherActiveLoans")
        active = [l for l in other_loans if l.get("loanNumber")]
        if active:
            lines.append("")
            lines.append(f"📂 *Otros préstamos activos ({len(active)}):*")
            for loan in active:
                days = loan.get("daysUntilDue", 0)
                due_date = loan.get("dueTime", "N/D")
                total = loan.get("totalAmountToPay", 0)
                late_fee = loan.get("lateFeeAmount", 0)

                status_icon = "🔴" if days < 0 else ("🟡" if days <= 5 else "🟢")
                lines.append(
                    f"  {status_icon} Préstamo #{loan['loanNumber']} — Vence: {due_date} — Total: RD$ {total:,.2f}"
                    + (f" (mora: RD$ {late_fee:,.2f})" if late_fee and late_fee > 0 else "")
                )

        if not lines:
            return "✅ No encontré préstamos activos asociados a su documento de identidad."

        return "\n".join(lines)