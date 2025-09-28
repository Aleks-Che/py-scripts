import argparse
import json
import os
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import urllib3
# Отключаем предупреждения о SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================
# Константы парсера
# ==============================
BASE_URL = "https://marvel.fandom.com"
# URL страницы категории по умолчанию (можно изменить при необходимости)
DEFAULT_PAGE_URL = "https://marvel.fandom.com/ru/wiki/%D0%9A%D0%B0%D1%82%D0%B5%D0%B3%D0%BE%D1%80%D0%B8%D1%8F:%D0%9E%D0%B1%D1%80%D0%B0%D0%B7%D1%8B_%D0%BF%D0%B5%D1%80%D1%81%D0%BE%D0%BD%D0%B0%D0%B6%D0%B5%D0%B9?from=%D0%9D%D0%B5%D0%B2%D0%B5%D1%81%D1%82%D0%B0+%D0%B4%D0%B5%D0%B2%D1%8F%D1%82%D0%B8+%D0%BF%D0%B0%D1%83%D0%BA%D0%BE%D0%B2"
# Путь к выходному файлу по умолчанию
DEFAULT_OUTPUT_FILE = "marvel-fandom/character_images.json"
# Режим работы с существующими файлами: 'continue', 'new', 'overwrite'
DEFAULT_FILE_MODE = "continue"
# Селектор, содержащий блоки со списками членов категории
SELECTOR_MEMBERS = "#mw-content-text > div.category-page__members"
# Класс обертки каждого списка
WRAPPER_CLASS = "category-page__members-wrapper"
# Класс списка внутри обертки
LIST_CLASS = "category-page__members-for-char"
# Класс отдельного элемента списка
ITEM_CLASS = "category-page__member"


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
    
    # Если это веб-URL
    try:
        import time
        import random
        
        # Методы обхода защиты
        def try_method_1():
            """Базовый метод с простыми заголовками"""
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            return requests.get(url, timeout=30, headers=headers, verify=False)
        
        def try_method_2():
            """Метод с ротацией User-Agent"""
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
            ]
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            return requests.get(url, timeout=30, headers=headers, verify=False)
        
        def try_method_3():
            """Метод с сессией и куками"""
            session = requests.Session()
            # Сначала получаем главную страницу для установки кук
            try:
                session.get('https://marvel.fandom.com/', timeout=10, verify=False)
            except:
                pass
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Referer': 'https://marvel.fandom.com/',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            return session.get(url, timeout=30, headers=headers, verify=False)
        
        def try_method_4():
            """Метод без SSL проверки и с прокси-поддержкой"""
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
            }
            # Пробуем с разными параметрами SSL
            return requests.get(url, timeout=30, headers=headers, verify=False, allow_redirects=True)
        
        def try_method_5():
            """Метод с использованием HTTP вместо HTTPS"""
            http_url = url.replace('https://', 'http://')
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
            }
            return requests.get(http_url, timeout=30, headers=headers, allow_redirects=True)
        
        def try_method_6():
            """Метод с использованием curl-cffi (если доступен)"""
            try:
                from curl_cffi import requests as curl_requests
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
                }
                response = curl_requests.get(url, headers=headers, impersonate="chrome110")
                return response
            except ImportError:
                raise Exception("curl_cffi не установлен")
        
        def try_method_7():
            """Метод с использованием cloudscraper (если доступен)"""
            try:
                import cloudscraper
                scraper = cloudscraper.create_scraper()
                response = scraper.get(url, timeout=30)
                return response
            except ImportError:
                raise Exception("cloudscraper не установлен")
        
        def try_method_8():
            """Метод с использованием Selenium WebDriver (если доступен)"""
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
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
            except ImportError:
                raise Exception("selenium не установлен")
        
        def try_method_9():
            """Метод с использованием Playwright (если доступен)"""
            try:
                from playwright.sync_api import sync_playwright
                
                with sync_playwright() as p:
                    # Запускаем браузер Chromium
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
                    )
                    
                    page = context.new_page()
                    
                    # Обходим обнаружение автоматизации
                    page.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                    """)
                    
                    # Переходим на страницу
                    page.goto(url, wait_until='networkidle')
                    
                    # Получаем HTML
                    html = page.content()
                    
                    browser.close()
                    return html
            except ImportError:
                raise Exception("playwright не установлен")
        
        # Список методов для попыток
        methods = [
                # try_method_1,
                # try_method_2,
                # try_method_3,
                # try_method_4,
                # try_method_5,
                # try_method_6,
                # try_method_7,
                try_method_8,
                try_method_9]
        
        for i, method in enumerate(methods):
            try:
                print(f"Попытка {i+1} методом {method.__name__}...")
                time.sleep(random.uniform(1, 3))  # Случайная задержка
                result = method()
                
                # Обработка разных типов результатов
                if hasattr(result, 'text'):
                    # Это response объект от requests
                    result.raise_for_status()
                    print(f"Успешно! Использован метод {method.__name__}")
                    return result.text
                elif isinstance(result, str):
                    # Это HTML строка от браузера
                    print(f"Успешно! Использован метод {method.__name__}")
                    return result
                else:
                    # Неожиданный тип результата
                    raise Exception(f"Неожиданный тип результата от {method.__name__}")
            except requests.exceptions.RequestException as e:
                print(f"Метод {i+1} не сработал: {str(e)[:100]}...")
                if i == len(methods) - 1:  # Последняя попытка
                    raise
                
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при загрузке страницы {url}: {e}")
        print("\nВсе методы обхода защиты не сработали.")
        print("Возможные причины:")
        print("1. Сайт блокирует ваш IP-адрес")
        print("2. Анти-DDoS защита активирована")
        print("3. Проблемы с сетевым подключением")
        print("4. Региональные ограничения")
        print("\nРекомендации:")
        print("1. Используйте локальный файл: --page-url file://path/to/file.html")
        print("2. Установите браузерные библиотеки:")
        print("   pip install selenium webdriver-manager")
        print("   или")
        print("   pip install playwright")
        print("3. Попробуйте использовать VPN или прокси")
        print("4. Подождите некоторое время и попробуйте снова")
        print("5. Проверьте, доступен ли сайт в браузере")
        print("6. Установите дополнительные библиотеки:")
        print("   pip install cloudscraper curl-cffi")
        print("7. Используйте Tor или другие анонимайзеры")
        print("8. Попробуйте мобильный интернет или другую сеть")
        raise


def parse_category_page(html: str) -> list[dict]:
    """
    Извлечь ссылки и названия из блока категории.

    Возвращает список словарей:
        {
            "title": <название страницы>,
            "url":   <полный URL>
        }
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(SELECTOR_MEMBERS)
    if not container:
        return []

    results = []

    # Находим все обертки списков
    wrappers = container.find_all("div", class_=WRAPPER_CLASS)
    for wrapper in wrappers:
        # Внутри каждой обертки ищем ul со списком
        ul = wrapper.find("ul", class_=LIST_CLASS)
        if not ul:
            continue
        # Проходим по каждому элементу списка
        for li in ul.find_all("li", class_=ITEM_CLASS):
            a_tag = li.find("a", href=True, title=True)
            if not a_tag:
                continue
            title = a_tag["title"].strip()
            href = a_tag["href"]
            full_url = urljoin(BASE_URL, href)
            results.append({"title": title, "url": full_url})

    return results


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
        description="Парсер категорий сайта marvel.fandom.com"
    )
    parser.add_argument(
        "--page-url",
        default=DEFAULT_PAGE_URL,
        help="URL страницы категории, которую нужно спарсить (по умолчанию используется DEFAULT_PAGE_URL). Можно указать локальный файл: file://path/to/file.html",
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
    args = parser.parse_args()

    # Используем значение по умолчанию, если URL не задан
    if not args.page_url:
        args.page_url = DEFAULT_PAGE_URL

    html = fetch_page(args.page_url)
    items = parse_category_page(html)

    if not items:
        print("Не удалось найти элементы на странице.")
        return

    # Сохраняем данные с учетом выбранного режима
    result_path = save_to_json(items, args.output, args.file_mode)
    if result_path:  # Если был создан новый файл
        args.output = result_path
    
    print(f"Сохранено {len(items)} элементов в {args.output}")


if __name__ == "__main__":
    main()