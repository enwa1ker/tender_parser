# parsers/kumtor_kg.py
# Парсит https://www.kumtor.kg/ru/category/procurement/

from parsers._base_parser import BaseParser
import re


class KumtorParser(BaseParser):
    SOURCE_NAME = "kumtor.kg"
    BASE_URL = "https://www.kumtor.kg/ru/category/procurement/"
    VERIFY_SSL = True

    SKIP = [
        "/category/", "/about/", "/deposit/", "/people-careers/",
        "/social-responsibility/", "/environment-protection/",
        "/media/", "/all-reports/", "/governance", "/contact",
        "/faq", "/health-safety", "/training", "/biodiversity",
        "/water", "/air-", "/waste-", "/energy-", "/news/",
        "/video/", "/jobs/", "/sales-of-illiquid",
        "informacziya-dlya", "bajlanysh", "telefon-doveriya",
        "kumtor-values", "selection-process",
    ]
    MONTHS = {
        "января":"01","февраля":"02","марта":"03","апреля":"04",
        "мая":"05","июня":"06","июля":"07","августа":"08",
        "сентября":"09","октября":"10","ноября":"11","декабря":"12",
    }

    def parse_page(self, page: int) -> list[dict]:
        url = self.BASE_URL if page == 1 else f"{self.BASE_URL}page/{page}/"
        soup = self.get_html(url)
        if not soup:
            return []

        tenders = []
        seen_ids = set()

        for link in soup.select("a[href]"):
            try:
                href = link.get("href", "")
                if not href or "kumtor.kg/ru/" not in href:
                    continue
                if any(p in href for p in self.SKIP):
                    continue

                text = link.get_text(strip=True)
                if not text or len(text) < 20:
                    continue

                # Дата в начале текста
                dm = re.match(r"^(\d{2}\.\d{2}\.\d{4})\s*", text)
                pub_date = dm.group(1) if dm else ""
                title = text[len(pub_date):].strip() if pub_date else text
                if not title or len(title) < 10:
                    continue

                # Дедлайн из текста
                deadline = ""
                dlm = re.search(
                    r"[«»\"']?(\d{1,2})[«»\"']?\s*(мая|июня|июля|августа|сентября|октября|ноября|декабря|января|февраля|марта|апреля)\s+(\d{4})",
                    title, re.IGNORECASE
                )
                if dlm:
                    d, m, y = dlm.group(1), dlm.group(2).lower(), dlm.group(3)
                    deadline = f"{d.zfill(2)}.{self.MONTHS.get(m,'00')}.{y}"

                slug = href.rstrip("/").split("/")[-1]
                tid = f"kumtor_{slug[:60]}"
                if tid in seen_ids:
                    continue
                seen_ids.add(tid)

                tenders.append({
                    "id": tid,
                    "source": self.SOURCE_NAME,
                    "title": title,
                    "url": href,
                    "customer": "Кумтор Голд Компани",
                    "amount": "",
                    "deadline": deadline,
                    "pub_date": pub_date,
                })
            except Exception as e:
                print(f"[{self.SOURCE_NAME}] ⚠️  {e}")

        return tenders


_parser = KumtorParser()

def get_tenders(pages: int = 2) -> list[dict]:
    return _parser.get_tenders(pages=pages)
