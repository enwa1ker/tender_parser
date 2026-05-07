# parsers/tenders_kg.py
# tenders.kg блокирует ботов через Cloudflare/DDos-Guard.
# Решение: используем Google Cache или альтернативный источник — osoo.kg
# который агрегирует тендеры с тех же порталов без блокировок.

import requests
from bs4 import BeautifulSoup
import urllib3
from config import REQUEST_TIMEOUT

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SOURCE_NAME = "tenders.kg"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Referer": "https://www.google.com/",
}


def _try_direct(session, page: int) -> list[dict]:
    """Попытка напрямую с Referer от Google."""
    try:
        params = {"f": "all"}
        if page > 1:
            params["page"] = page
        resp = session.get(
            "https://www.tenders.kg/Announcements_list.php",
            params=params,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        return _parse_html(resp.text)
    except Exception:
        return []


def _try_osoo_kg(page: int) -> list[dict]:
    """
    Резервный источник: osoo.kg агрегирует тендеры КГ.
    Работает без блокировок.
    """
    try:
        resp = requests.get(
            "https://www.osoo.kg/tender/",
            params={"page": page},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        tenders = []
        for row in soup.select("table tr, .tender-item, .tender-row"):
            link_el = row.select_one("a[href]")
            if not link_el:
                continue
            title = link_el.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            href = link_el.get("href", "")
            url = href if href.startswith("http") else f"https://www.osoo.kg{href}"
            tenders.append({
                "id": f"tenderskg_osoo_{abs(hash(title + href))}",
                "source": SOURCE_NAME,
                "title": title,
                "url": url,
                "customer": "",
                "amount": "",
                "deadline": "",
                "pub_date": "",
            })
        return tenders
    except Exception:
        return []


def _parse_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    tenders = []
    for row in soup.select("table tr"):
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
            tid = f"tenders_kg_{href.split('id=')[-1] if 'id=' in href else abs(hash(title))}"
            deadline = ""
            customer = ""
            for col in cols[1:]:
                t = col.get_text(strip=True)
                if len(t) == 10 and t[2] == "." and t[5] == ".":
                    deadline = t
                elif t and len(t) > 5:
                    customer = t
            tenders.append({
                "id": tid,
                "source": SOURCE_NAME,
                "title": title,
                "url": url,
                "customer": customer,
                "amount": "",
                "deadline": deadline,
                "pub_date": "",
            })
        except Exception:
            continue
    return tenders


def get_tenders(pages: int = 2) -> list[dict]:
    result = []
    session = requests.Session()
    # Сначала заходим на главную для куков
    try:
        session.get("https://www.tenders.kg/", headers=HEADERS, timeout=10)
    except Exception:
        pass

    for page in range(1, pages + 1):
        tenders = _try_direct(session, page)
        if not tenders:
            print(f"[{SOURCE_NAME}] ⚠️  Прямой доступ заблокирован, пробуем osoo.kg...")
            tenders = _try_osoo_kg(page)
        result.extend(tenders)
        print(f"[{SOURCE_NAME}] стр.{page}: {len(tenders)} тендеров")

    return result
