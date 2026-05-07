# parsers/_base_parser.py
# Базовый класс для всех парсеров.
# Все парсеры должны наследоваться от BaseParser.

import requests
from bs4 import BeautifulSoup
from config import REQUEST_TIMEOUT


class BaseParser:
    SOURCE_NAME = "unknown"
    BASE_URL = ""

    def get_html(self, url: str, params: dict = None) -> BeautifulSoup | None:
        """
        Делает GET-запрос с таймаутом и возвращает BeautifulSoup.
        При ошибке логирует и возвращает None — парсер не падает насмерть.
        """
        try:
            resp = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,          # ← КРИТИЧНО: без этого парсер висит вечно
                headers={"User-Agent": "Mozilla/5.0 (compatible; TenderBot/2.0)"},
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
        """Переопределить в каждом парсере. Возвращает список тендеров."""
        raise NotImplementedError

    def get_tenders(self, pages: int = 2) -> list[dict]:
        """Собирает тендеры со всех страниц."""
        result = []
        for page in range(1, pages + 1):
            try:
                tenders = self.parse_page(page)
                result.extend(tenders)
                print(f"[{self.SOURCE_NAME}] стр.{page}: {len(tenders)} тендеров")
            except Exception as e:
                print(f"[{self.SOURCE_NAME}] ❌ Ошибка на стр.{page}: {e}")
        return result
