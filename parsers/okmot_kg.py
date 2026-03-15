# parsers/okmot_kg.py — парсер zakupki.okmot.kg

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://zakupki.okmot.kg"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get_tenders(pages: int = 2) -> list[dict]:
    """Возвращает тендеры с первых N страниц zakupki.okmot.kg"""

    tenders = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for page in range(1, pages + 1):
        url = f"{BASE_URL}/popp/view/order/list.xhtml?page={page}"
        print(f"[okmot.kg] Загружаю страницу {page}...")

        try:
            response = session.get(url, verify=False, timeout=15)
            response.encoding = "utf-8"
        except requests.exceptions.RequestException as e:
            print(f"[okmot.kg] Ошибка на странице {page}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        # Здесь таблиц 2 — тендеры во второй (индекс 1)
        tables = soup.find_all("table")
        if len(tables) < 2:
            print(f"[okmot.kg] Таблица не найдена на странице {page}")
            continue

        tender_table = tables[1]
        rows = tender_table.find_all("tr")
        found_on_page = 0

        for row in rows:
            cells = row.find_all("td")

            if len(cells) < 9:
                continue

            try:
                customer = cells[1].get_text(strip=True, separator=" ")
                customer = customer.replace("Name of company", "").strip()

                title = cells[3].get_text(strip=True, separator=" ")
                title = title.replace("purchase Name", "").strip()

                amount = cells[6].get_text(strip=True, separator=" ")
                amount = amount.replace("Planned amount", "").strip()

                deadline = cells[8].get_text(strip=True, separator=" ")
                deadline = deadline.replace("Bids Submission Deadline", "").strip()

                link_tag = cells[4].find("a", href=True)
                if not link_tag:
                    continue

                href = link_tag["href"]
                if href.startswith("view.xhtml"):
                    full_url = f"{BASE_URL}/popp/view/order/{href}"
                elif href.startswith("/"):
                    full_url = BASE_URL + href
                else:
                    full_url = href

                tender_id = f"okmot_kg_{href.split('id=')[-1]}"

                if not title or len(title) < 5:
                    continue

                tenders.append({
                    "id":       tender_id,
                    "title":    title,
                    "customer": customer,
                    "deadline": deadline,
                    "amount":   amount,
                    "url":      full_url,
                    "source":   "zakupki.okmot.kg",
                    "found_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
                })
                found_on_page += 1

            except Exception as e:
                print(f"[okmot.kg] Ошибка в строке: {e}")
                continue

        print(f"[okmot.kg] На странице {page}: {found_on_page} тендеров")
        time.sleep(2)

    print(f"[okmot.kg] Итого найдено: {len(tenders)}")
    return tenders