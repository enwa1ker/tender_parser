# parsers/okmot_kg.py
# VERIFY_SSL = False — сайт использует самоподписанный сертификат

from parsers._base_parser import BaseParser


class OkmotParser(BaseParser):
    SOURCE_NAME = "zakupki.okmot.kg"
    BASE_URL = "https://zakupki.okmot.kg/popp/view/request/list.xhtml"
    VERIFY_SSL = False  # ← госсайт, проблемный SSL

    def parse_page(self, page: int) -> list[dict]:
        params = {"currentPage": page - 1} if page > 1 else {}
        soup = self.get_html(self.BASE_URL, params=params)
        if not soup:
            return []

        tenders = []
        rows = soup.select("table tbody tr, .ui-datatable tbody tr")

        for row in rows:
            try:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue

                link_el = row.select_one("a[href]")
                title_el = cols[1] if len(cols) > 1 else None
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                if not title or len(title) < 5:
                    continue

                href = link_el.get("href", "") if link_el else ""
                url = href if href.startswith("http") else f"https://zakupki.okmot.kg{href}"

                num_col = cols[0].get_text(strip=True)
                tender_id = f"okmot_{num_col}" if num_col else f"okmot_{abs(hash(title))}"

                customer = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                deadline = cols[4].get_text(strip=True) if len(cols) > 4 else ""
                amount = cols[3].get_text(strip=True) if len(cols) > 3 else ""

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

        return tenders


_parser = OkmotParser()

def get_tenders(pages: int = 2) -> list[dict]:
    return _parser.get_tenders(pages=pages)
