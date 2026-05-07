# parsers/okmot_kg.py
# Правильный URL: /popp/view/order/list.xhtml (не request)
# VERIFY_SSL = False — самоподписанный сертификат

from parsers._base_parser import BaseParser


class OkmotParser(BaseParser):
    SOURCE_NAME = "zakupki.okmot.kg"
    BASE_URL = "https://zakupki.okmot.kg/popp/view/order/list.xhtml"
    VERIFY_SSL = False

    def parse_page(self, page: int) -> list[dict]:
        # JSF-сайт — пагинация через параметр строки запроса не работает,
        # парсим только первую страницу (свежие объявления)
        soup = self.get_html(self.BASE_URL)
        if not soup:
            return []

        tenders = []
        rows = soup.select("table tbody tr, .ui-datatable-data tr")

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
                url = href if href.startswith("http") else f"https://zakupki.okmot.kg{href}"

                num_col = cols[0].get_text(strip=True)
                tender_id = f"okmot_{num_col.replace('/', '_')}" if num_col else f"okmot_{abs(hash(title))}"

                customer = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                deadline = cols[-1].get_text(strip=True) if cols else ""
                amount = ""
                for col in cols:
                    t = col.get_text(strip=True)
                    if any(c.isdigit() for c in t) and len(t) > 4 and len(t) < 20:
                        if "." not in t[:3]:  # не дата
                            amount = t
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
                print(f"[{self.SOURCE_NAME}] ⚠️  {e}")

        # Только первая страница — JSF не поддерживает GET-пагинацию
        return tenders if page == 1 else []


_parser = OkmotParser()

def get_tenders(pages: int = 2) -> list[dict]:
    return _parser.get_tenders(pages=pages)
