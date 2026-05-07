# parsers/tenders_kg.py
# tenders.kg блокирует простые запросы — используем сессию с куками и referer

import requests
from bs4 import BeautifulSoup
import urllib3
from config import REQUEST_TIMEOUT

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SOURCE_NAME = "tenders.kg"
BASE_URL = "https://www.tenders.kg/Announcements_list.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Referer": "https://www.tenders.kg/",
}


def _get_session():
    """Создаём сессию — сначала заходим на главную чтобы получить куки."""
    session = requests.Session()
    try:
        session.get("https://www.tenders.kg/", headers=HEADERS, timeout=REQUEST_TIMEOUT)
    except Exception:
        pass
    return session


def _parse_page(session, page: int) -> list[dict]:
    params = {"f": "all"}
    if page > 1:
        params["page"] = page

    try:
        resp = session.get(BASE_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
    except requests.HTTPError as e:
        print(f"[{SOURCE_NAME}] ❌ HTTP {e.response.status_code}")
        return []
    except Exception as e:
        print(f"[{SOURCE_NAME}] ❌ {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    tenders = []

    # tenders.kg использует таблицу для списка тендеров
    rows = soup.select("table tr")
    for row in rows:
        try:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            link_el = row.select_one("a[href]")
            if not link_el:
                continue

            title = link_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            href = link_el.get("href", "")
            url = href if href.startswith("http") else f"https://www.tenders.kg/{href.lstrip('/')}"

            tender_id = f"tenders_kg_{href.split('id=')[-1] if 'id=' in href else abs(hash(title))}"

            customer, deadline, amount = "", "", ""
            for i, col in enumerate(cols):
                text = col.get_text(strip=True)
                if i == 1 and link_el in col.find_all("a"):
                    continue
                if any(c.isdigit() for c in text):
                    if "." in text and len(text) <= 12:
                        deadline = text
                    elif len(text) > 3:
                        customer = text

            tenders.append({
                "id": tender_id,
                "source": SOURCE_NAME,
                "title": title,
                "url": url,
                "customer": customer,
                "amount": amount,
                "deadline": deadline,
                "pub_date": "",
            })
        except Exception as e:
            print(f"[{SOURCE_NAME}] ⚠️  {e}")

    return tenders


def get_tenders(pages: int = 2) -> list[dict]:
    session = _get_session()
    result = []
    for page in range(1, pages + 1):
        tenders = _parse_page(session, page)
        result.extend(tenders)
        print(f"[{SOURCE_NAME}] стр.{page}: {len(tenders)} тендеров")
    return result
