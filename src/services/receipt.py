import io
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

import os

# Регистрируем шрифт с поддержкой кириллицы
_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_FONT_REGISTERED = False


def _ensure_font():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    font_path = os.path.join(_FONT_DIR, "DejaVuSans.ttf")
    bold_path = os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("DejaVu", font_path))
    if os.path.exists(bold_path):
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", bold_path))
    _FONT_REGISTERED = True


def _font(bold: bool = False) -> str:
    _ensure_font()
    if bold and _FONT_REGISTERED and "DejaVu-Bold" in pdfmetrics.getRegisteredFontNames():
        return "DejaVu-Bold"
    if _FONT_REGISTERED and "DejaVu" in pdfmetrics.getRegisteredFontNames():
        return "DejaVu"
    return "Helvetica-Bold" if bold else "Helvetica"


def generate_receipt(
    payment_id: int,
    user_name: str,
    amount: float,
    currency: str,
    payment_type: str,
    created_at: datetime,
) -> bytes:
    """
    Генерирует PDF-квитанцию об оплате и возвращает байты файла.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Фон шапки
    c.setFillColor(colors.HexColor("#1a1a2e"))
    c.rect(0, height - 60 * mm, width, 60 * mm, fill=1, stroke=0)

    # Заголовок
    c.setFillColor(colors.white)
    c.setFont(_font(bold=True), 22)
    c.drawCentredString(width / 2, height - 25 * mm, "🔮 AI-бот Таро")
    c.setFont(_font(), 12)
    c.drawCentredString(width / 2, height - 35 * mm, "Квитанция об оплате")

    # Декоративная линия
    c.setStrokeColor(colors.HexColor("#e94560"))
    c.setLineWidth(2)
    c.line(20 * mm, height - 65 * mm, width - 20 * mm, height - 65 * mm)

    # Блок с данными
    c.setFillColor(colors.HexColor("#0f3460"))
    c.roundRect(20 * mm, height - 145 * mm, width - 40 * mm, 70 * mm, 5, fill=1, stroke=0)

    def draw_row(label: str, value: str, y: float):
        c.setFont(_font(), 11)
        c.setFillColor(colors.HexColor("#a0a0b0"))
        c.drawString(30 * mm, y, label)
        c.setFont(_font(bold=True), 11)
        c.setFillColor(colors.white)
        c.drawRightString(width - 30 * mm, y, value)

    y = height - 85 * mm
    draw_row("Номер квитанции:", f"#{payment_id:06d}", y)
    draw_row("Плательщик:", user_name, y - 12 * mm)
    draw_row("Дата оплаты:", created_at.strftime("%d.%m.%Y %H:%M UTC"), y - 24 * mm)
    draw_row("Услуга:", _payment_type_label(payment_type), y - 36 * mm)
    draw_row("Сумма:", _format_amount(amount, currency), y - 48 * mm)

    # Итоговая сумма крупно
    c.setStrokeColor(colors.HexColor("#e94560"))
    c.setLineWidth(1)
    c.line(20 * mm, height - 155 * mm, width - 20 * mm, height - 155 * mm)

    c.setFont(_font(bold=True), 18)
    c.setFillColor(colors.HexColor("#1a1a2e"))
    c.drawCentredString(width / 2, height - 170 * mm, f"Итого: {_format_amount(amount, currency)}")

    # Статус
    c.setFillColor(colors.HexColor("#27ae60"))
    c.roundRect(width / 2 - 30 * mm, height - 185 * mm, 60 * mm, 10 * mm, 4, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(_font(bold=True), 12)
    c.drawCentredString(width / 2, height - 179 * mm, "✓ ОПЛАЧЕНО")

    # Подвал
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.setFont(_font(), 9)
    c.setFillColor(colors.HexColor("#888888"))
    c.drawCentredString(width / 2, 25 * mm, "Этот документ является подтверждением оплаты.")
    c.drawCentredString(width / 2, 18 * mm, "По вопросам обращайтесь через бота.")

    c.save()
    return buf.getvalue()


def _payment_type_label(payment_type: str) -> str:
    labels = {
        "pro_sub": "Подписка PRO (1 месяц)",
        "single_spread": "Глубокий разбор (разовый)",
    }
    return labels.get(payment_type, payment_type)


def _format_amount(amount: float, currency: str) -> str:
    if currency == "XTR":
        return f"{int(amount)} ⭐ Stars"
    return f"{amount:.2f} ₽"
