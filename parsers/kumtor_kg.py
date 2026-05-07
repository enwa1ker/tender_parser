# parsers/kumtor_kg.py
# Парсер закупок kumtor.kg
# Kumtor часто обновляется ночью — поэтому в расписании есть прогон в 02:00

from parsers._base_parser import BaseParser
from datetime import datetime


class KumtorParser(BaseParser):
    SOURCE_NAME = "kumtor.kg"
    BASE_URL = "https://www.kumtor.kg/ru/category/procurement/"

    def parse_page(self, page: int) -> list[dict]:
        url = self.BASE_URL if page == 1 else f"{self.BASE_URL}page/{page}/"
        soup = self.get_html(url)
        if not soup:
            return []

        tenders = []
        # Ищем карточки тендеров
        articles = soup.select("article.post, .procurement-item, .entry-content article")

        for article in articles:
            try:
                title_el = article.select_one("h2 a, h3 a, .entry-title a")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                url_link = title_el.get("href", "")

                date_el = article.select_one("time, .date, .post-date")
                pub_date = date_el.get("datetime", "") if date_el else ""

                tender_id = f"kumtor_{url_link.split('/')[-2] if url_link else title[:30]}"

                tenders.append({
                    "id": tender_id,
                    "source": self.SOURCE_NAME,
                    "title": title,
                    "url": url_link,
                    "customer": "Kumtor Gold Company",
                    "amount": "",
                    "deadline": "",
                    "pub_date": pub_date,
                })
            except Exception as e:
                print(f"[{self.SOURCE_NAME}] ⚠️  Ошибка парсинга карточки: {e}")
                continue

        return tenders


# Фабричная функция — main.py вызывает именно её
_parser = KumtorParser()

def get_tenders(pages: int = 2) -> list[dict]:
    return _parser.get_tenders(pages=pages)
