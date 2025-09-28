import argparse
import json
import os
import time
import random
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==============================
# Константы парсера для страницы "Все страницы"
# ==============================
BASE_URL = "https://marvel.fandom.com"
# URL страницы "Все страницы" по умолчанию
DEFAULT_PAGE_URL = "https://marvel.fandom.com/wiki/Special:AllPages"
# Путь к выходному файлу по умолчанию
DEFAULT_OUTPUT_FILE = "marvel-fandom-en/all_pages.json"
# Режим работы с существующими файлами: 'continue', 'new', 'overwrite'
DEFAULT_FILE_MODE = "continue"
# Селектор для блока со списком страниц
SELECTOR_PAGES_LIST = "#mw-content-text > div.mw-allpages-body"
# Селектор для блока навигации (ссылка на следующую страницу)
SELECTOR_NEXT_PAGE = "div.mw-allpages-nav"


def fetch_page(url: str) -> str:
    """Скачать HTML страницы или загрузить из локального файла."""
    # Проверяем, является ли URL локальным файлом
    if url.startswith('file://') or os.path.isfile(url):
        file_path = url.replace('file://', '')
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Ошибка при чтении файла {file_path}: {e}")
            raise
    
    # Если это веб-URL - используем только 8-й метод (Selenium)
    try:
        # Настройки Chrome для обхода защиты
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36')
        
        # Запускаем браузер в фоновом режиме
        chrome_options.add_argument('--headless')
        
        driver = webdriver.Chrome(options=chrome_options)
        try:
            # Устанавливаем скрипт для обхода обнаружения автоматизации
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Загружаем страницу
            driver.get(url)
            
            # Ждем загрузки контента
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Дополнительная задержка для полной загрузки
            time.sleep(3)
            
            # Получаем HTML
            html = driver.page_source
            return html
        finally:
            driver.quit()
    except Exception as e:
        print(f"Ошибка при загрузке страницы {url}: {e}")
        print("\nМетод Selenium не сработал.")
        print("Возможные причины:")
        print("1. Selenium не установлен: pip install selenium")
        print("2. ChromeDriver не установлен или не в PATH")
        print("3. Сайт блокирует ваш IP-адрес")
        print("4. Проблемы с сетевым подключением")
        raise


def parse_all_pages(html: str) -> list[dict]:
    """
    Извлечь ссылки и названия из блока "Все страницы".
    
    Возвращает список словарей:
        {
            "title": <название страницы>,
            "url":   <полный URL>
        }
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(SELECTOR_PAGES_LIST)
    if not container:
        print("Не найден блок со списком страниц")
        return []

    results = []
    
    # Находим все элементы списка
    list_items = container.find_all("li")
    for li in list_items:
        a_tag = li.find("a", href=True, title=True)
        if not a_tag:
            continue
        
        title = a_tag.get("title", "").strip()
        href = a_tag["href"]
        full_url = urljoin(BASE_URL, href)
        
        results.append({"title": title, "url": full_url})
    
    print(f"Найдено {len(results)} страниц на текущей странице")
    return results


def get_next_page_url(html: str) -> str:
    """
    Найти URL следующей страницы.
    
    Возвращает полный URL следующей страницы или пустую строку, если следующей страницы нет.
    """
    soup = BeautifulSoup(html, "html.parser")
    nav_container = soup.select_one(SELECTOR_NEXT_PAGE)
    
    if not nav_container:
        print("Не найден блок навигации")
        return ""
    
    # Ищем ссылку "Следующая страница" (русская версия)
    next_link = nav_container.find("a", string=lambda text: text and "Следующая страница" in text)
    
    # Если не найдена русская версия, ищем английскую "Next page"
    if not next_link:
        next_link = nav_container.find("a", string=lambda text: text and "Next page" in text)
    
    if not next_link:
        print("Не найдена ссылка на следующую страницу (ни русская, ни английская)")
        return ""
    
    href = next_link.get("href", "")
    if href:
        full_url = urljoin(BASE_URL, href)
        print(f"Найдена следующая страница: {full_url}")
        return full_url
    
    return ""


def get_next_filename(base_path: str) -> str:
    """Получить следующее имя файла с нумерацией."""
    directory = os.path.dirname(base_path)
    filename = os.path.basename(base_path)
    name, ext = os.path.splitext(filename)
    
    counter = 1
    while True:
        new_path = os.path.join(directory, f"{name}_{counter}{ext}")
        if not os.path.exists(new_path):
            return new_path
        counter += 1


def load_existing_data(file_path: str) -> list[dict]:
    """Загрузить существующие данные из JSON файла."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_to_json(data: list[dict], output_path: str, file_mode: str = 'continue'):
    """Сохранить полученные данные в JSON‑файл с учетом режима."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if file_mode == 'continue' and os.path.exists(output_path):
        # Продолжаем существующий файл
        existing_data = load_existing_data(output_path)
        # Удаляем дубликаты по URL
        existing_urls = {item['url'] for item in existing_data}
        new_data = [item for item in data if item['url'] not in existing_urls]
        combined_data = existing_data + new_data
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2)
        print(f"Добавлено {len(new_data)} новых элементов к существующим {len(existing_data)}")
        
    elif file_mode == 'new':
        # Создаем новый файл с нумерацией
        new_path = get_next_filename(output_path)
        with open(new_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Создан новый файл: {new_path}")
        return new_path  # Возвращаем новый путь
        
    else:  # overwrite
        # Перезаписываем файл
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Перезаписан файл: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Парсер страницы 'Все страницы' сайта marvel.fandom.com"
    )
    parser.add_argument(
        "--page-url",
        default=DEFAULT_PAGE_URL,
        help="URL страницы 'Все страницы', которую нужно спарсить (по умолчанию используется DEFAULT_PAGE_URL). Можно указать локальный файл: file://path/to/file.html",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        help="Путь к файлу JSON для сохранения результатов (по умолчанию используется DEFAULT_OUTPUT_FILE)",
    )
    parser.add_argument(
        "--file-mode",
        choices=['continue', 'new', 'overwrite'],
        default=DEFAULT_FILE_MODE,
        help="Режим работы с существующим файлом: continue - продолжить список, new - создать новый файл с нумерацией, overwrite - перезаписать (по умолчанию: continue)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Максимальное количество страниц для парсинга (0 - без ограничений)",
    )
    parser.add_argument(
        "--continue-from",
        help="URL страницы, с которой продолжить парсинг (если файл уже существует)",
    )
    args = parser.parse_args()

    # Используем значение по умолчанию, если URL не задан
    if not args.page_url:
        args.page_url = DEFAULT_PAGE_URL

    # Определяем начальную страницу
    if args.continue_from:
        current_url = args.continue_from
        print(f"Продолжаем парсинг с: {current_url}")
    else:
        current_url = args.page_url
    
    page_count = 0
    total_items = 0
    
    # Загружаем существующие данные для подсчета общего количества
    if os.path.exists(args.output) and args.file_mode == 'continue':
        existing_data = load_existing_data(args.output)
        total_items = len(existing_data)
        print(f"Найдено существующих элементов: {total_items}")
    
    while current_url:
        page_count += 1
        print(f"\n=== Страница {page_count} ===")
        print(f"Загружаем: {current_url}")
        
        # Проверяем ограничение по количеству страниц
        if args.max_pages > 0 and page_count > args.max_pages:
            print(f"Достигнут лимит в {args.max_pages} страниц")
            break
        
        try:
            html = fetch_page(current_url)
            items = parse_all_pages(html)
            
            if not items:
                print("Не удалось найти элементы на странице.")
                break
            
            # Сохраняем данные с учетом выбранного режима
            save_to_json(items, args.output, args.file_mode)
            total_items += len(items)
            print(f"Сохранено {len(items)} элементов (всего: {total_items})")
            
            # Ищем следующую страницу
            next_url = get_next_page_url(html)
            if not next_url:
                print("Следующая страница не найдена. Парсинг завершен.")
                break
            
            current_url = next_url
            
            # Случайная задержка между страницами
            delay = random.uniform(2, 5)
            print(f"Ждем {delay:.1f} секунд перед следующей страницей...")
            time.sleep(delay)
            
        except Exception as e:
            print(f"Ошибка при обработке страницы {current_url}: {e}")
            break
    
    print(f"\n=== Парсинг завершен ===")
    print(f"Обработано страниц: {page_count}")
    print(f"Всего собрано элементов: {total_items}")
    print(f"Результаты сохранены в: {args.output}")


if __name__ == "__main__":
    main()