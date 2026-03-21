# integrations/telegram_bot.py

import requests
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, GOOGLE_SHEET_ID, TELEGRAM_ADMIN_IDS

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
                [
                    {
                        "text": btn["text"],
                        **({"url": btn["url"]} if btn.get("url") else {"callback_data": btn.get("data", "")}),
                    }
                ]
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


def _sheet_url() -> str:
    if not GOOGLE_SHEET_ID:
        return ""
    return f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"


def broadcast(text: str, buttons: list = None) -> bool:
    from core.database import get_subscribers
    subscribers = get_subscribers()
    targets = [s["chat_id"] for s in subscribers] if subscribers else [str(x).strip() for x in TELEGRAM_CHAT_IDS if str(x).strip()]
    ok = True
    for cid in targets:
        ok = send_message(text, chat_id=cid, buttons=buttons) and ok
    return ok


def notify_tender(tender: dict) -> bool:
    """Отправляет уведомление о новом тендере всем подписчикам"""
    buttons = []
    if tender.get("url"):
        buttons.append({"text": "🔗 Открыть тендер", "url": tender.get("url")})
    if _sheet_url():
        buttons.append({"text": "📊 В таблицу", "url": _sheet_url()})
    return broadcast(format_tender_message(tender), buttons=buttons)


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
        print(f"[Telegram] getUpdates {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[Telegram] Ошибка getUpdates: {e}")
    return []


def handle_commands():
    """
    Проверяет новые команды от пользователей и отвечает на них.
    Вызывается из main.py в основном цикле.
    """
    from core.database import (
        get_stats,
        get_last_tenders,
        subscribe,
        unsubscribe,
        get_subscribers,
        kv_get,
        kv_set,
    )

    # Offset храним в SQLite (на Railway файловая система не всегда сохраняется между рестартами).
    # Фоллбек: старый telegram_offset.txt (локально).
    offset = 0
    offset_str = kv_get("telegram:offset")
    if offset_str and offset_str.isdigit():
        offset = int(offset_str)
    else:
        offset_file = "telegram_offset.txt"
        try:
            with open(offset_file) as f:
                offset = int(f.read().strip())
        except Exception:
            offset = 0

    if not TELEGRAM_BOT_TOKEN:
        return

    def _is_admin(chat_id: str) -> bool:
        if not TELEGRAM_ADMIN_IDS:
            # если админы не настроены — считаем админом только первый TELEGRAM_CHAT_ID (старый режим)
            fallback = str(TELEGRAM_CHAT_IDS[0]).strip() if TELEGRAM_CHAT_IDS else ""
            return bool(fallback) and str(chat_id).strip() == fallback
        return str(chat_id).strip() in set(TELEGRAM_ADMIN_IDS)

    def _send_list(chat_id: str, page: int = 1):
        PAGE_SIZE = 5
        tenders = get_last_tenders(100)  # берём последние 100

        if not tenders:
            send_message("📭 Тендеров пока нет.", chat_id=chat_id)
            return

        total = len(tenders)
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        page = max(1, min(page, total_pages))  # защита от выхода за границы

        start = (page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        page_tenders = tenders[start:end]

        msg = f"📋 <b>Тендеры (стр. {page} из {total_pages}):</b>\n\n"
        for i, t in enumerate(page_tenders, start + 1):
            title = t["title"][:55] + "..." if len(t["title"]) > 55 else t["title"]
            msg += f"{i}. <a href='{t['url']}'>{title}</a>\n"
            msg += f"   📅 {t['found_at']} | {t['source']}\n\n"

        # Кнопки навигации
        buttons = []
        if page > 1:
            buttons.append({"text": "◀", "data": f"список:{page-1}"})
        buttons.append({"text": f"{page}/{total_pages}", "data": "нет"})
        if page < total_pages:
            buttons.append({"text": "▶", "data": f"список:{page+1}"})

        # Отправляем в одну строку
        reply_markup = {
            "inline_keyboard": [
                [
                    *([{"text": "◀", "callback_data": f"список:{page-1}"}] if page > 1 else []),
                    {"text": f"{page}/{total_pages}", "callback_data": "нет"},
                    *([{"text": "▶", "callback_data": f"список:{page+1}"}] if page < total_pages else []),
                ]
            ]
        }

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id":    chat_id,
            "text":       msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": reply_markup,
        }, timeout=10)

    def _send_status(chat_id: str):
        stats = get_stats()
        total = sum(stats.values())
        msg = f"📊 <b>Статистика:</b>\n\nВсего найдено: <b>{total}</b>\n\n"
        for source, count in stats.items():
            msg += f"• {source}: {count}\n"
        send_message(msg, chat_id=chat_id)

    def _send_help(chat_id: str):
        subs_count = len(get_subscribers())
    
        # Постоянная клавиатура внизу
        keyboard_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(keyboard_url, json={
            "chat_id": chat_id,
            "text": (
                "👋 Привет! Я мониторю тендеры.\n\n"
                "Выбери действие:"
            ),
            "parse_mode": "HTML",
            "reply_markup": {
                "keyboard": [
                    [{"text": "📋 Список тендеров"}, {"text": "📊 Статистика"}],
                    [{"text": "✅ Подписаться"},      {"text": "⛔ Отписаться"}],
                ],
                "resize_keyboard": True,
                "persistent": True,
            }
        }, timeout=10)

    def _send_subscribers(chat_id: str):
        # Получаем список подписчиков с их именами (если есть) и датой добавления и отсупыв формате "дата и время"
        subs = get_subscribers()
        if not subs:
            send_message("Подписчиков пока нет.", chat_id=chat_id)
            return
        msg = f"👥 <b>Подписчики ({len(subs)}):</b>\n\n"
        for s in subs:
            name = s["username"] if s["username"] else f"id: {s['chat_id']}"
            msg += f"• {name} — с {s['added_at']}\n"
        send_message(msg, chat_id=chat_id)

    updates = get_updates(offset)
    if not updates:
        # Если offset "улетел" в будущее, бот никогда не увидит новые апдейты.
        # Восстановление: берём список апдейтов с offset=0 и просто выставляем offset на последний id+1.
        if offset > 0:
            probe = get_updates(0)
            if probe:
                max_id = max([u.get("update_id", -1) for u in probe if isinstance(u.get("update_id"), int)] or [-1])
                if max_id >= 0:
                    kv_set("telegram:offset", str(max_id + 1))
        return
        return

    max_update_id = offset - 1

    for update in updates:
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            max_update_id = max(max_update_id, update_id)

       # 1) Обработка нажатий на inline-кнопки
        callback = update.get("callback_query")
        if callback:
            chat_id = str(callback.get("message", {}).get("chat", {}).get("id", "")).strip()
            data = str(callback.get("data", "")).strip().lower()
            if not chat_id:
                continue

            if data == "список":
                _send_list(chat_id, page=1)
            elif data.startswith("список:"):
                try:
                    page = int(data.split(":")[1])
                except Exception:
                    page = 1
                _send_list(chat_id, page=page)
            elif data == "статус":
                _send_status(chat_id)
            elif data == "стоп":
                unsubscribed = unsubscribe(chat_id)
                send_message(
                    "⛔ Вы отписались.\nНапишите /старт чтобы снова подписаться."
                    if unsubscribed
                    else "⛔ Вы уже были отписаны.\nНапишите /старт чтобы подписаться.",
                    chat_id=chat_id,
                )
            elif data == "нет":
                pass  # нажали на номер страницы — ничего не делаем
            continue

        # 2) Обработка обычных команд (/start, /статус, /список, /стоп)
        # 2) Обработка обычных команд (/start, /статус, /список, /стоп)
        msg_obj = update.get("message") or update.get("edited_message")
        if not msg_obj:
            continue

        chat_id = str(msg_obj.get("chat", {}).get("id", "")).strip()
        text = str(msg_obj.get("text", "")).strip()
        if not chat_id or not text:
            continue

        # Извлекаем username — добавь эти строки сюда
        username = msg_obj.get("from", {}).get("username", "") or ""
        first_name = msg_obj.get("from", {}).get("first_name", "") or ""
        display_name = f"@{username}" if username else first_name

        cmd = text.split()[0].strip().lower()
        if "@" in cmd:
            cmd = cmd.split("@", 1)[0]
        if cmd in ("/start", "/старт"):
            subscribe(chat_id, username=display_name)  # ← добавили display_name
            _send_help(chat_id)
        elif text == "📋 Список тендеров":
            _send_list(chat_id)
        elif text == "📊 Статистика":
            _send_status(chat_id)
        elif text == "✅ Подписаться":
            subscribe(chat_id, username=display_name)  # ← добавили display_name
            send_message("✅ Вы подписаны!", chat_id=chat_id)
        elif text == "⛔ Отписаться":
            unsubscribe(chat_id)
            send_message("⛔ Вы отписались.", chat_id=chat_id)
        elif cmd in ("/help",):
            _send_help(chat_id)
        elif cmd in ("/список", "/list"):
            _send_list(chat_id)
        elif cmd in ("/статус", "/status"):
            _send_status(chat_id)
        elif cmd in ("/стоп", "/stop"):
            unsubscribed = unsubscribe(chat_id)
            send_message(
                "⛔ Ок, вы отписались. Напишите /старт чтобы снова включить."
                if unsubscribed
                else "⛔ Вы уже отписаны. Напишите /старт чтобы подписаться.",
                chat_id=chat_id,
            )
        elif cmd in ("/подписчики", "/subs"):
            if not _is_admin(chat_id):
                send_message("⛔ Недостаточно прав.", chat_id=chat_id)
            else:
                _send_subscribers(chat_id)
        elif cmd in ("/добавить", "/add"):
            if not _is_admin(chat_id):
                send_message("⛔ Недостаточно прав.", chat_id=chat_id)
            else:
                parts = text.split()
                if len(parts) < 2:
                    send_message("Формат: /добавить chat_id", chat_id=chat_id)
                else:
                    target = parts[1].strip()
                    subscribe(target)
                    send_message(f"✅ Добавил подписчика <code>{target}</code>", chat_id=chat_id)
        elif cmd in ("/удалить", "/remove", "/del"):
            if not _is_admin(chat_id):
                send_message("⛔ Недостаточно прав.", chat_id=chat_id)
            else:
                parts = text.split()
                if len(parts) < 2:
                    send_message("Формат: /удалить chat_id", chat_id=chat_id)
                else:
                    target = parts[1].strip()
                    ok = unsubscribe(target)
                    send_message(
                        f"✅ Удалил подписчика <code>{target}</code>" if ok else f"ℹ️ Подписчик <code>{target}</code> не найден",
                        chat_id=chat_id,
                    )

    # Сохраняем новый offset (следующий после последнего update_id)
    new_offset = max_update_id + 1 if max_update_id >= 0 else offset
    kv_set("telegram:offset", str(new_offset))

    # Локальный фоллбек (не критично, если не получится)
    try:
        with open("telegram_offset.txt", "w") as f:
            f.write(str(new_offset))
    except Exception:
        pass