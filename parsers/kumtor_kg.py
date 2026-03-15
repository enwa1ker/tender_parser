# parsers/kumtor_kg.py — парсер kumtor.kg

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.kumtor.kg"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get_tenders(pages: int = 2) -> list[dict]:
    """Возвращает тендеры с первых N страниц kumtor.kg"""

    tenders = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for page in range(1, pages + 1):
        if page == 1:
            url = f"{BASE_URL}/ru/category/procurement/"
        else:
            url = f"{BASE_URL}/ru/category/procurement/page/{page}/"

        print(f"[kumtor.kg] Загружаю страницу {page}...")

        try:
            response = session.get(url, headers=HEADERS, verify=False, timeout=15)
            response.encoding = "utf-8"
        except requests.exceptions.RequestException as e:
            print(f"[kumtor.kg] Ошибка на странице {page}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        found_on_page = 0

        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)

            # Тендеры начинаются с даты формата ДД.ММ.ГГГГ
            # Пример: "13.03.2026ПОСТАВКА ФРИКЦИОННЫХ АНКЕРОВ..."
            date_match = re.match(r"^(\d{2}\.\d{2}\.\d{4})(.*)", text)
            if not date_match:
                continue

            # Пропускаем навигационные ссылки
            skip_patterns = [
                "/about/", "/deposit/", "/people/", "/social/",
                "/environment/", "/media/", "/category/news/",
                "/category/video/", "/governance/", "procurement/page/",
                "/category/announcements/", "satyp-aluular"
            ]
            if any(p in href for p in skip_patterns):
                continue

            published_date = date_match.group(1)  # "13.03.2026"
            title = date_match.group(2).strip()    # "ПОСТАВКА ФРИКЦИОННЫХ..."

            # Убираем текст дедлайна из названия если он там есть
            # "НАЗВАНИЕ КРАЙНИЙ СРОК ПОДАЧИ ЗАЯВКИ: 16:00..."
            if "КРАЙНИЙ СРОК" in title:
                title = title.split("КРАЙНИЙ СРОК")[0].strip()

            if not title or len(title) < 5:
                continue

            # Уникальный ID — последняя часть ссылки
            tender_id = f"kumtor_kg_{href.rstrip('/').split('/')[-1][:50]}"

            tenders.append({
                "id":         tender_id,
                "title":      title,
                "customer":   "Кумтор Голд Компани",  # всегда один заказчик
                "deadline":   "",
                "amount":     "",
                "url":        href,
                "source":     "kumtor.kg",
                "found_at":   datetime.now().strftime("%d.%m.%Y %H:%M"),
                "published":  published_date,
            })
            found_on_page += 1

        print(f"[kumtor.kg] На странице {page}: {found_on_page} тендеров")
        time.sleep(2)

    # Убираем дубли
    seen = set()
    unique = []
    for t in tenders:
        if t["id"] not in seen:
            seen.add(t["id"])
            unique.append(t)

    print(f"[kumtor.kg] Итого найдено: {len(unique)}")
    return unique