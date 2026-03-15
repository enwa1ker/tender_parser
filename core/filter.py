# core/filter.py — фильтр тендеров по ключевым словам

from config import KEYWORDS


def is_relevant(title: str, description: str = "") -> bool:
    """
    Проверяет — подходит ли тендер нам?
    Ищет ключевые слова в названии и описании (без учёта регистра).

    title       — название тендера
    description — описание (если есть на сайте)

    Возвращает True если тендер наш, False если нет.
    """

    # Объединяем название и описание в одну строку для поиска
    # Переводим в нижний регистр — чтобы "Электрика" и "электрика" совпадали
    text = (title + " " + description).lower()

    for keyword in KEYWORDS:
        if keyword.lower() in text:
            return True   # нашли совпадение — тендер наш

    return False  # ни одно слово не совпало


def find_matched_keywords(title: str, description: str = "") -> list:
    """
    Вспомогательная функция — возвращает список слов которые совпали.
    Удобно для отладки: видно почему тендер был отобран.
    """
    text = (title + " " + description).lower()

    matched = []
    for keyword in KEYWORDS:
        if keyword.lower() in text:
            matched.append(keyword)

    return matched