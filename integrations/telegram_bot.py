# integrations/telegram_bot.py

import requests
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS

logger = logging.getLogger(__name__)


# ── Простая отправка сообщений ───────────────────────────────────────────────

def send_message(text: str, chat_id: str = None, buttons: list = None) -> bool:
    """Отправляет сообщение одному или всем подписчикам"""
    if not TELEGRAM_BOT_TOKEN:
        print("[Telegram] Токен не настроен")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    targets = [chat_id] if chat_id else TELEGRAM_CHAT_IDS

    # Формируем кнопки если есть
    reply_markup = None
    if buttons:
        reply_markup = {
            "inline_keyboard": [
                [{"text": btn["text"], "callback_data": btn["data"]}]
                for btn in buttons
            ]
        }

    success = True
    for cid in targets:
        cid = str(cid).strip()
        if not cid:
            continue
        try:
            payload = {
                "chat_id":    cid,
                "text":       text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup

            response = requests.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                print(f"[Telegram] Ошибка {response.status_code}: {response.text}")
                success = False
        except Exception as e:
            print(f"[Telegram] Ошибка: {e}")
            success = False

    return success


def format_tender_message(tender: dict) -> str:
    """Форматирует тендер в красивое сообщение"""
    source_icons = {
        "tenders.kg":       "🔵",
        "zakupki.gov.kg":   "🟢",
        "zakupki.okmot.kg": "🟡",
        "kumtor.kg":        "🔴",
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
    """Отправляет уведомление о новом тендере"""
    return send_message(format_tender_message(tender))


def notify_error(error_text: str):
    """Отправляет уведомление об ошибке"""
    send_message(f"⚠️ <b>Ошибка парсера</b>\n\n{error_text}")


# ── Обработка команд ─────────────────────────────────────────────────────────

def get_updates(offset: int = 0) -> list:
    """Получает новые сообщения от пользователей"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        response = requests.get(url, params={"offset": offset, "timeout": 5}, timeout=10)
        if response.status_code == 200:
            return response.json().get("result", [])
    except Exception as e:
        print(f"[Telegram] Ошибка getUpdates: {e}")
    return []


def handle_commands():
    """
    Проверяет новые команды от пользователей и отвечает на них.
    Вызывается из main.py в основном цикле.
    """
    from core.database import get_stats, get_last_tenders

    # Читаем последний обработанный offset из файла
    offset_file = "telegram_offset.txt"
    try:
        with open(offset_file) as f:
            offset = int(f.read().strip())
    except Exception:
        offset = 0

    updates = get_updates(offset)

    # Обработка нажатий на кнопки
    for update in get_updates(offset - len(updates) if updates else offset):
        callback = update.get("callback_query", {})
        if not callback:
            continue
        chat_id = str(callback.get("message", {}).get("chat", {}).get("id", ""))
        data = callback.get("data", "")

        if data == "список":
            # Та же логика что и /список
            tenders = get_last_tenders(10)
            if not tenders:
                send_message("📭 Тендеров пока нет.", chat_id=chat_id)
            else:
                msg = "📋 <b>Последние 10 тендеров:</b>\n\n"
                for i, t in enumerate(tenders, 1):
                    title = t['title'][:55] + "..." if len(t['title']) > 55 else t['title']
                    msg += f"{i}. <a href='{t['url']}'>{title}</a>\n"
                    msg += f"   📅 {t['found_at']} | {t['source']}\n\n"
                send_message(msg, chat_id=chat_id)

        elif data == "статус":
            from core.database import get_stats
            stats = get_stats()
            total = sum(stats.values())
            msg = f"📊 <b>Статистика:</b>\n\nВсего найдено: <b>{total}</b>\n\n"
            for source, count in stats.items():
                msg += f"• {source}: {count}\n"
            send_message(msg, chat_id=chat_id)

        elif data == "стоп":
            send_message(
                "⛔ Вы отписались.\nНапишите /start чтобы снова подписаться.",
                chat_id=chat_id
            )
    # Сохраняем новый offset
    with open(offset_file, "w") as f:
        f.write(str(offset))