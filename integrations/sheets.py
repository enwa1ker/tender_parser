# integrations/sheets.py
# Работа с Google Sheets — добавление тендеров, форматирование, защита от дублей.
 
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import time
 
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS, SHEET_COLUMNS, SHEET_ALL_TAB
 
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
 
_client = None
_sheet = None
 
 
def init_sheets():
    global _client, _sheet
 
    # ── Railway / GitHub Actions: читаем из переменной окружения ──
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds_info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        print("[sheets] 🔑 Credentials загружены из переменной окружения")
    else:
        # ── Локальная разработка: читаем из файла ─────────────────
        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS, scopes=SCOPES)
        print("[sheets] 🔑 Credentials загружены из файла")
 
    _client = gspread.authorize(creds)
    _sheet = _client.open_by_key(GOOGLE_SHEET_ID)
    _ensure_tab(_sheet, SHEET_ALL_TAB)
    print(f"[sheets] ✅ Подключено к Google Sheets")
 
 
def _ensure_tab(sheet, tab_name: str):
    """Создаёт вкладку с заголовками если её нет."""
    try:
        ws = sheet.worksheet(tab_name)
        headers = ws.row_values(1)
        if not headers:
            ws.insert_row(SHEET_COLUMNS, 1)
            _format_header(ws)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=tab_name, rows=1000, cols=len(SHEET_COLUMNS))
        ws.insert_row(SHEET_COLUMNS, 1)
        _format_header(ws)
    return ws
 
 
def _format_header(ws):
    """Делает шапку таблицы жирной с цветом."""
    try:
        ws.format("A1:I1", {
            "backgroundColor": {"red": 0.18, "green": 0.36, "blue": 0.62},
            "textFormat": {
                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                "bold": True,
                "fontSize": 10,
            },
            "horizontalAlignment": "CENTER",
        })
        ws.freeze(rows=1)
    except Exception as e:
        print(f"[sheets] ⚠️  Не удалось форматировать шапку: {e}")
 
 
def _days_until(deadline_str: str) -> str:
    """Считает дней до дедлайна. Возвращает строку или пусто."""
    if not deadline_str:
        return ""
    formats = ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    for fmt in formats:
        try:
            d = datetime.strptime(deadline_str.strip()[:10], fmt).date()
            delta = (d - date.today()).days
            if delta < 0:
                return "просрочен"
            return str(delta)
        except ValueError:
            continue
    return ""
 
 
def add_tender(tender: dict):
    """Добавляет тендер в главную вкладку и в вкладку источника."""
    global _sheet
 
    ws_all = _sheet.worksheet(SHEET_ALL_TAB)
 
    source_tab = tender.get("source", "Прочие")
    ws_src = _ensure_tab(_sheet, source_tab)
 
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    deadline = tender.get("deadline", "")
    days_left = _days_until(deadline)
 
    row = [
        now,
        tender.get("title", ""),
        tender.get("customer", ""),
        tender.get("amount", ""),
        deadline,
        days_left,
        tender.get("source", ""),
        tender.get("url", ""),
        "Новый",
    ]
 
    ws_all.append_row(row, value_input_option="USER_ENTERED")
    time.sleep(0.5)
    ws_src.append_row(row, value_input_option="USER_ENTERED")
 
    try:
        if days_left.isdigit() and int(days_left) <= 3:
            last_row = len(ws_all.get_all_values())
            ws_all.format(f"A{last_row}:I{last_row}", {
                "backgroundColor": {"red": 1.0, "green": 0.9, "blue": 0.8}
            })
    except Exception:
        pass
 
    print(f"[sheets] ✅ Добавлен: {tender.get('title', '')[:60]}")
