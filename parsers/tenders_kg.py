# parsers/tenders_kg.py

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.tenders.kg"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def create_session():
    """Создаёт сессию и входит как гость"""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(f"{BASE_URL}/menu.php", verify=False, timeout=15)
    session.post(f"{BASE_URL}/menu.php", data={"guest": "1"}, verify=False, timeout=15)
    return session


def get_tenders(pages: int = 2) -> list[dict]:
    """
    Возвращает тендеры с первых N страниц.
    pages=2 — берём 2 страницы (около 30 тендеров), этого достаточно
    чтобы поймать новые за последние 3 часа.
    """
    session = create_session()
    tenders = []

    for page in range(1, pages + 1):
        url = f"{BASE_URL}/Announcements_list.php?goto={page}"
        print(f"[tenders.kg] Загружаю страницу {page}...")

        try:
            response = session.get(url, verify=False, timeout=15)
            response.encoding = "utf-8"
        except requests.exceptions.RequestException as e:
            print(f"[tenders.kg] Ошибка на странице {page}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        # Ищем все ссылки на конкретные тендеры
        links = soup.find_all("a", href=True)

        for link in links:
            href = link["href"]
            title_text = link.get_text(strip=True)

            # Нас интересуют только ссылки вида Announcements_view.php?editid1=XXXXX
            if "Announcements_view.php?editid1=" not in href:
                continue

            if not title_text or len(title_text) < 5:
                continue

            # Извлекаем ID тендера из ссылки
            tender_id = href.split("editid1=")[-1]

            # Убираем номер из начала названия — "№29073. Название" → "Название"
            # Формат: "№12345. Текст"
            if ". " in title_text:
                title = title_text.split(". ", 1)[-1]
            else:
                title = title_text

            full_url = f"{BASE_URL}/{href}"

            tenders.append({
                "id":       f"tenders_kg_{tender_id}",
                "title":    title,
                "customer": "",    # загрузим со страницы тендера если нужно
                "deadline": "",
                "amount":   "",
                "url":      full_url,
                "source":   "tenders.kg",
                "found_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
            })

    print(f"[tenders.kg] Итого найдено: {len(tenders)}")
    return tenders