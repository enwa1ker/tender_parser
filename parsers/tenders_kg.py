# parsers/tenders_kg.py

import requests
import ssl
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.tenders.kg"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def create_session():
    """Создаёт сессию и входит как гость"""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.verify = False

    try:
        session.get(f"{BASE_URL}/menu.php", timeout=15)
        session.post(f"{BASE_URL}/menu.php", data={"guest": "1"}, timeout=15)
    except Exception as e:
        print(f"[tenders.kg] Ошибка входа: {e}")

    return session


def get_tenders(pages: int = 2) -> list[dict]:
    """Возвращает тендеры с первых N страниц tenders.kg"""

    tenders = []

    try:
        session = create_session()
    except Exception as e:
        print(f"[tenders.kg] Ошибка создания сессии: {e}")
        return []

    for page in range(1, pages + 1):
        url = f"{BASE_URL}/Announcements_list.php?goto={page}"
        print(f"[tenders.kg] Загружаю страницу {page}...")

        try:
            response = session.get(url, timeout=15)
            response.encoding = "utf-8"
        except Exception as e:
            print(f"[tenders.kg] Ошибка на странице {page}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=True)
        found_on_page = 0

        for link in links:
            href = link["href"]
            title_text = link.get_text(strip=True)

            if "Announcements_view.php?editid1=" not in href:
                continue
            if not title_text or len(title_text) < 5:
                continue

            tender_id = href.split("editid1=")[-1]

            if ". " in title_text:
                title = title_text.split(". ", 1)[-1]
            else:
                title = title_text

            full_url = f"{BASE_URL}/{href}"

            tenders.append({
                "id":       f"tenders_kg_{tender_id}",
                "title":    title,
                "customer": "",
                "deadline": "",
                "amount":   "",
                "url":      full_url,
                "source":   "tenders.kg",
                "found_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
            })
            found_on_page += 1

        print(f"[tenders.kg] На странице {page}: {found_on_page} тендеров")
        time.sleep(2)

    seen = set()
    unique = []
    for t in tenders:
        if t["id"] not in seen:
            seen.add(t["id"])
            unique.append(t)

    print(f"[tenders.kg] Итого найдено: {len(unique)}")
    return unique