# parsers/gov_kg.py
# Новый портал ЭГЗ — goszakupki.okmot.kg
# VERIFY_SSL = False — самоподписанный сертификат

import requests
import json
from config import REQUEST_TIMEOUT
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SOURCE_NAME = "goszakupki.okmot.kg"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Referer": "https://goszakupki.okmot.kg/public/home",
}

# Пробуем API эндпоинт (сайт на Angular/React — данные через API)
API_URLS = [
    "https://goszakupki.okmot.kg/api/public/announcements",
    "https://goszakupki.okmot.kg/api/lots",
    "https://goszakupki.okmot.kg/api/tenders",
]


def _try_api(page: int) -> list[dict]:
    """Пробуем получить данные через JSON API."""
    for api_url in API_URLS:
        try:
            resp = requests.get(
                api_url,
                params={"page": page - 1, "size": 20, "locale": "ru"},
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                verify=False,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("content", data.get("items", data.get("data", [])))
                if items:
                    return _parse_items(items)
        except Exception:
            continue
    return []


def _parse_items(items: list) -> list[dict]:
    tenders = []
    for item in items:
        try:
            title = item.get("name") or item.get("title") or item.get("subject") or ""
            if not title:
                continue
            tid = str(item.get("id") or item.get("lotId") or abs(hash(title)))
            tenders.append({
                "id": f"govkg_{tid}",
                "source": SOURCE_NAME,
                "title": title,
                "url": item.get("url") or f"https://goszakupki.okmot.kg/public/lots/{tid}",
                "customer": item.get("customer") or item.get("buyerName") or "",
                "amount": str(item.get("amount") or item.get("price") or ""),
                "deadline": item.get("deadline") or item.get("submissionDeadline") or "",
                "pub_date": item.get("publishDate") or item.get("createdAt") or "",
            })
        except Exception:
            continue
    return tenders


def get_tenders(pages: int = 2) -> list[dict]:
    result = []
    for page in range(1, pages + 1):
        tenders = _try_api(page)
        result.extend(tenders)
        print(f"[{SOURCE_NAME}] стр.{page}: {len(tenders)} тендеров")
    return result
