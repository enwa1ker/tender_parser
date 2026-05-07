# parsers/gov_kg.py
# Портал: https://goszakupki.okmot.kg/public/home

from parsers._base_parser import BaseParser


class GovKgParser(BaseParser):
    SOURCE_NAME = "goszakupki.okmot.kg"
    BASE_URL = "https://goszakupki.okmot.kg/public/lots"

    def parse_page(self, page: int) -> list[dict]:
        params = {"page": page - 1, "size": 20, "locale": "ru"}
        soup = self.get_html(self.BASE_URL, params=params)
        if not soup:
            return []

        tenders = []

        # Карточки лотов
        cards = soup.select(".lot-card, .tender-card, .announcement-item, article, .card")

        for card in cards:
            try:
                link_el = card.select_one("a[href]")
                title_el = card.select_one("h3, h4, .title, .lot-title, .name")

                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                if not title or len(title) < 5:
                    continue

                href = link_el.get("href", "") if link_el else ""
                url = href if href.startswith("http") else f"https://goszakupki.okmot.kg{href}"

                # ID
                lot_id = href.split("/")[-1] if href else abs(hash(title))
                tender_id = f"govkg_{lot_id}"

                # Заказчик и сумма
                customer_el = card.select_one(".customer, .organizer, .buyer")
                customer = customer_el.get_text(strip=True) if customer_el else ""

                amount_el = card.select_one(".amount, .price, .sum")
                amount = amount_el.get_text(strip=True) if amount_el else ""

                deadline_el = card.select_one(".deadline, .date-end, .end-date")
                deadline = deadline_el.get_text(strip=True) if deadline_el else ""

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
                print(f"[{self.SOURCE_NAME}] ⚠️  Ошибка парсинга карточки: {e}")
                continue

        return tenders


_parser = GovKgParser()

def get_tenders(pages: int = 2) -> list[dict]:
    return _parser.get_tenders(pages=pages)
