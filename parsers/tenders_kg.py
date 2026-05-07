# parsers/tenders_kg.py

from parsers._base_parser import BaseParser


class TendersKgParser(BaseParser):
    SOURCE_NAME = "tenders.kg"
    BASE_URL = "https://www.tenders.kg/Announcements_list.php"

    def parse_page(self, page: int) -> list[dict]:
        params = {"f": "all", "page": page} if page > 1 else {"f": "all"}
        soup = self.get_html(self.BASE_URL, params=params)
        if not soup:
            return []

        tenders = []
        rows = soup.select("table.tenders-table tr, .announcement-row, table tr")

        for row in rows:
            try:
                cols = row.find_all("td")
                if len(cols) < 3:
                    continue

                link_el = row.select_one("a[href]")
                if not link_el:
                    continue

                title = link_el.get_text(strip=True)
                if not title or len(title) < 5:
                    continue

                href = link_el.get("href", "")
                url = href if href.startswith("http") else f"https://www.tenders.kg/{href.lstrip('/')}"

                # ID из URL или из текста
                tender_id = f"tenders_kg_{href.split('id=')[-1] if 'id=' in href else abs(hash(title))}"

                # Дедлайн и сумма — ищем по позиции колонок
                deadline = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                customer = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                amount = ""
                for col in cols:
                    text = col.get_text(strip=True)
                    if any(c.isdigit() for c in text) and ("сом" in text.lower() or "KGS" in text or "KGZ" in text):
                        amount = text
                        break

                tenders.append({
                    "id": tender_id,
                    "source": self.SOURCE_NAME,
                    "title": title,
                    "url": url,
                    "customer": customer,
                    "amount": amount,
                    "deadline": deadline,
                    "pub_date": "",
                })
            except Exception as e:
                print(f"[{self.SOURCE_NAME}] ⚠️  Ошибка парсинга строки: {e}")
                continue

        return tenders


_parser = TendersKgParser()

def get_tenders(pages: int = 2) -> list[dict]:
    return _parser.get_tenders(pages=pages)
