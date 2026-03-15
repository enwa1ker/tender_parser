# integrations/telegram_bot.py — отправка уведомлений в Telegram

import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS


def send_message(text: str) -> bool:
    """
    Отправляет сообщение всем подписчикам из TELEGRAM_CHAT_IDS.
    Возвращает True если успешно, False если ошибка.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("[Telegram] Токен не настроен — пропускаем")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    success = True

    for chat_id in TELEGRAM_CHAT_IDS:
        chat_id = chat_id.strip()
        if not chat_id:
            continue

        try:
            response = requests.post(url, json={
                "chat_id":    chat_id,
                "text":       text,
                "parse_mode": "HTML",  # поддержка жирного текста и ссылок
            }, timeout=10)

            if response.status_code == 200:
                print(f"[Telegram] Сообщение отправлено → {chat_id}")
            else:
                print(f"[Telegram] Ошибка {response.status_code}: {response.text}")
                success = False

        except requests.exceptions.RequestException as e:
            print(f"[Telegram] Ошибка подключения: {e}")
            success = False

    return success


def format_tender_message(tender: dict) -> str:
    """
    Форматирует тендер в красивое сообщение для Telegram.
    HTML теги: <b>жирный</b>, <i>курсив</i>, <a href=''>ссылка</a>
    """

    # Иконка зависит от источника
    source_icons = {
        "tenders.kg":      "🔵",
        "zakupki.gov.kg":  "🟢",
        "zakupki.okmot.kg":"🟡",
        "kumtor.kg":       "🔴",
    }
    icon = source_icons.get(tender.get("source", ""), "⚡")

    lines = []
    lines.append(f"{icon} <b>НОВЫЙ ТЕНДЕР</b> — {tender.get('source', '')}")
    lines.append("")
    lines.append(f"📋 <b>{tender.get('title', '')}</b>")

    if tender.get("customer"):
        lines.append(f"🏛 Заказчик: {tender.get('customer')}")

    if tender.get("amount"):
        lines.append(f"💰 Сумма: {tender.get('amount')} сом")

    if tender.get("deadline"):
        lines.append(f"⏰ Дедлайн: {tender.get('deadline')}")

    lines.append("")
    lines.append(f"🔗 <a href='{tender.get('url', '')}'>Открыть тендер</a>")

    return "\n".join(lines)


def notify_tender(tender: dict) -> bool:
    """Главная функция — форматирует и отправляет уведомление о тендере"""
    message = format_tender_message(tender)
    return send_message(message)


def notify_error(error_text: str):
    """Отправляет уведомление об ошибке парсера"""
    message = f"⚠️ <b>Ошибка парсера</b>\n\n{error_text}"
    send_message(message)


def notify_stats(stats: dict):
    """Отправляет статистику запуска"""
    lines = ["📊 <b>Статистика проверки</b>", ""]
    for source, count in stats.items():
        lines.append(f"• {source}: найдено {count} новых")
    message = "\n".join(lines)
    send_message(message)