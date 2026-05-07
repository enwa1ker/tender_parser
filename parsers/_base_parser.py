# parsers/_base_parser.py

import requests
from bs4 import BeautifulSoup
import urllib3
from config import REQUEST_TIMEOUT

# Отключаем предупреждения о SSL — кыргызские госсайты используют
# самоподписанные сертификаты, verify=False для них неизбежен
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Реальный браузерный User-Agent — обходит 403 на tenders.kg
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class BaseParser:
    SOURCE_NAME = "unknown"
    BASE_URL = ""
    VERIFY_SSL = True  # Переопределяй в False для госсайтов с плохим SSL

    def get_html(self, url: str, params: dict = None) -> BeautifulSoup | None:
        try:
            resp = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
                verify=self.VERIFY_SSL,
                headers={
                    "User-Agent": BROWSER_UA,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                },
            )
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return BeautifulSoup(resp.text, "html.parser")
        except requests.Timeout:
            print(f"[{self.SOURCE_NAME}] ⏱ Таймаут {REQUEST_TIMEOUT}с на {url}")
            return None
        except requests.HTTPError as e:
            print(f"[{self.SOURCE_NAME}] ❌ HTTP {e.response.status_code} на {url}")
            return None
        except requests.RequestException as e:
            print(f"[{self.SOURCE_NAME}] ❌ Сетевая ошибка: {e}")
            return None

    def parse_page(self, page: int) -> list[dict]:
        raise NotImplementedError

    def get_tenders(self, pages: int = 2) -> list[dict]:
        result = []
        for page in range(1, pages + 1):
            try:
                tenders = self.parse_page(page)
                result.extend(tenders)
                print(f"[{self.SOURCE_NAME}] стр.{page}: {len(tenders)} тендеров")
            except Exception as e:
                print(f"[{self.SOURCE_NAME}] ❌ Ошибка на стр.{page}: {e}")
        return result
