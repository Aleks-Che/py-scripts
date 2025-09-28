import json
import os
import time
import random
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Импорты для Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# ==============================
# Константы для парсинга контента
# ==============================
INPUT_DIR = "marvel-fandom/output"  # Каталог с JSON файлами со списками
OUTPUT_DIR = "marvel-fandom/parsed_content"  # Выходной каталог
MAIN_CONTENT_SELECTOR = "body > div.main-container > div.resizable-container > div.page.has-right-rail > main"
BASE_URL = "https://marvel.fandom.com"

# Настройки времени паузы
SHORT_PAUSE_MIN = 3  # Минимальная пауза между запросами (секунды)
SHORT_PAUSE_MAX = 5  # Максимальная пауза между запросами (секунды)
LONG_PAUSE_MIN = 10   # Минимальная длинная пауза (секунды)
LONG_PAUSE_MAX = 25  # Максимальная длинная пауза (секунды)
PAGES_BEFORE_LONG_PAUSE = 10  # Количество страниц перед длинной паузой

def setup_selenium_driver():
    """Настроить Selenium WebDriver для парсинга."""
    if not SELENIUM_AVAILABLE:
        raise Exception("selenium не установлен. Установите: pip install selenium webdriver-manager")
    
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
        
        # Устанавливаем скрипт для обхода обнаружения автоматизации
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    except Exception as e:
        raise Exception(f"Ошибка при настройке драйвера: {e}")

def fetch_page_with_selenium(driver, url: str) -> str:
    """Получить HTML страницы с помощью Selenium."""
    try:
        print(f"Загрузка страницы: {url}")
        driver.get(url)
        
        # Ждем загрузки основного контента
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "main"))
        )
        
        # Дополнительная задержка для полной загрузки динамического контента
        time.sleep(random.uniform(2, 4))
        
        return driver.page_source
    except Exception as e:
        print(f"Ошибка при загрузке страницы {url}: {e}")
        raise

def parse_main_content(html: str) -> dict:
    """Извлечь основной контент из страницы."""
    soup = BeautifulSoup(html, "html.parser")
    
    # Ищем основной контент по селектору
    main_content = soup.select_one(MAIN_CONTENT_SELECTOR)
    
    if not main_content:
        # Если не найден по точному селектору, ищем альтернативные варианты
        main_content = soup.find("main", class_="page__main")
        if not main_content:
            main_content = soup.find("div", id="content")
            if not main_content:
                print("Предупреждение: не найден основной контент по селекторам")
                return {"error": "Main content not found", "html_snippet": str(soup.find("body"))[:500]}
    
    # Извлекаем текстовое содержимое
    content_data = {
        "title": "",
        "url": "",
        "main_content": "",
        "sections": [],
        "infobox": {},
        "categories": [],
        "raw_html": str(main_content)
    }
    
    # Заголовок страницы
    title_elem = soup.find("h1", id="firstHeading") or soup.find("h1", class_="page-header__title")
    if title_elem:
        content_data["title"] = title_elem.get_text(strip=True)
    
    # Инфобокс (если есть)
    infobox = main_content.find("aside", class_="portable-infobox")
    if infobox:
        content_data["infobox"] = parse_infobox(infobox)
    
    # Секции статьи
    sections = main_content.find_all(["h2", "h3", "h4"])
    for section in sections:
        section_data = {
            "level": int(section.name[1]),
            "title": section.get_text(strip=True),
            "content": ""
        }
        
        # Собираем контент до следующего заголовка
        current = section.find_next_sibling()
        content_parts = []
        while current and current.name not in ["h2", "h3", "h4"]:
            if current.name == "p":
                content_parts.append(current.get_text(strip=True))
            elif current.name in ["ul", "ol"]:
                items = [li.get_text(strip=True) for li in current.find_all("li")]
                content_parts.extend(items)
            current = current.find_next_sibling()
        
        section_data["content"] = "\n".join(content_parts)
        content_data["sections"].append(section_data)
    
    # Основной текст (первые несколько абзацев)
    paragraphs = main_content.find_all("p", limit=10)
    content_data["main_content"] = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
    
    # Категории
    categories = soup.find_all("a", href=lambda x: x and "/wiki/Категория:" in x)
    content_data["categories"] = list(set([cat.get_text(strip=True) for cat in categories]))
    
    return content_data

def parse_infobox(infobox) -> dict:
    """Парсинг инфобокса с информацией о персонаже."""
    infobox_data = {}
    
    # Заголовок инфобокса
    title_elem = infobox.find("h2", class_="pi-item pi-title")
    if title_elem:
        infobox_data["name"] = title_elem.get_text(strip=True)
    
    # Группы данных
    groups = infobox.find_all("section", class_="pi-item pi-group")
    for group in groups:
        group_title = group.find("h2", class_="pi-header")
        if group_title:
            group_name = group_title.get_text(strip=True)
            infobox_data[group_name] = {}
            
            # Поля в группе
            items = group.find_all("div", class_="pi-item pi-data")
            for item in items:
                label = item.find("h3", class_="pi-data-label")
                value = item.find("div", class_="pi-data-value")
                if label and value:
                    key = label.get_text(strip=True).rstrip(":")
                    infobox_data[group_name][key] = value.get_text(strip=True)
    
    return infobox_data

def is_file_fully_processed(json_file_path: str) -> bool:
    """Проверить, обработан ли весь файл (все ссылки из JSON)."""
    # Проверяем существование входного файла
    if not os.path.exists(json_file_path):
        return False
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            links_data = json.load(f)
    except Exception as e:
        print(f"Ошибка при чтении файла {json_file_path}: {e}")
        return False
    
    if not isinstance(links_data, list):
        return False
    
    file_name = Path(json_file_path).stem
    output_subdir = os.path.join(OUTPUT_DIR, file_name)
    
    # Если выходной каталог не существует, файл точно не обработан
    if not os.path.exists(output_subdir):
        return False
    
    # Подсчитываем количество JSON файлов в выходном каталоге
    try:
        processed_files = [f for f in os.listdir(output_subdir) if f.endswith('.json')]
    except Exception as e:
        print(f"Ошибка при чтении каталога {output_subdir}: {e}")
        return False
    
    # Проверяем, совпадает ли количество обработанных файлов с количеством ссылок
    return len(processed_files) >= len(links_data)

def process_json_file(json_file_path: str, driver) -> None:
    """Обработать один JSON файл со списком ссылок."""
    print(f"\nОбработка файла: {json_file_path}")
    
    # Проверяем существование входного файла
    if not os.path.exists(json_file_path):
        print(f"Ошибка: входной файл {json_file_path} не существует")
        return
    
    # Загружаем список ссылок
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            links_data = json.load(f)
    except Exception as e:
        print(f"Ошибка при чтении файла {json_file_path}: {e}")
        return
    
    if not isinstance(links_data, list):
        print(f"Ошибка: файл {json_file_path} должен содержать список")
        return
    
    # Проверяем, обработан ли уже весь файл
    if is_file_fully_processed(json_file_path):
        print(f"Файл {json_file_path} уже полностью обработан. Пропуск.")
        return
    
    # Создаем выходную директорию для этого файла
    file_name = Path(json_file_path).stem
    output_subdir = os.path.join(OUTPUT_DIR, file_name)
    os.makedirs(output_subdir, exist_ok=True)
    
    print(f"Найдено {len(links_data)} ссылок для обработки")
    
    # Считаем уже обработанные файлы
    try:
        processed_files = [f for f in os.listdir(output_subdir) if f.endswith('.json')]
        processed_count = len(processed_files)
        if processed_count > 0:
            print(f"Уже обработано {processed_count} страниц")
    except Exception as e:
        print(f"Ошибка при чтении выходного каталога {output_subdir}: {e}")
        processed_count = 0
    
    # Обрабатываем каждую ссылку
    for i, item in enumerate(links_data):
        if not isinstance(item, dict) or 'url' not in item:
            print(f"Пропуск элемента {i}: неверный формат")
            continue
        
        url = item['url']
        title = item.get('title', f'item_{i}')
        
        # Очищаем название для использования в имени файла
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:100]  # Ограничиваем длину
        
        output_file = os.path.join(output_subdir, f"{safe_title}.json")
        
        # Проверяем, не обработана ли уже эта страница
        if os.path.exists(output_file):
            print(f"Пропуск {title}: уже обработано")
            continue
        
        try:
            # Загружаем страницу
            html = fetch_page_with_selenium(driver, url)
            
            # Парсим контент
            content_data = parse_main_content(html)
            content_data['url'] = url
            content_data['title'] = title
            
            # Сохраняем результат
            try:
                # Создаем родительские каталоги если их нет
                output_dir = os.path.dirname(output_file)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                    print(f"Создан каталог: {output_dir}")
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(content_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Ошибка при сохранении файла {output_file}: {e}")
                raise
            
            print(f"✓ Обработано: {title} ({i+1}/{len(links_data)})")
            
            # Случайная задержка между запросами
            time.sleep(random.uniform(SHORT_PAUSE_MIN, SHORT_PAUSE_MAX))
            
        except Exception as e:
            print(f"✗ Ошибка при обработке {title}: {e}")
            # Создаем файл с ошибкой
            error_data = {
                "error": str(e),
                "url": url,
                "title": title,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            try:
                # Создаем родительские каталоги если их нет
                output_dir = os.path.dirname(output_file)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                    print(f"Создан каталог: {output_dir}")
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(error_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Ошибка при сохранении файла с ошибкой {output_file}: {e}")
        
        # Каждые N страниц делаем длинную паузу
        if (i + 1) % PAGES_BEFORE_LONG_PAUSE == 0:
            print(f"Длинная пауза после {i + 1} страниц...")
            time.sleep(random.uniform(LONG_PAUSE_MIN, LONG_PAUSE_MAX))

def main():
    """Основная функция."""
    print("Запуск парсера контента marvel.fandom.com")
    print(f"Входной каталог: {INPUT_DIR}")
    print(f"Выходной каталог: {OUTPUT_DIR}")
    
    # Создаем выходной каталог
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Проверяем существование входного каталога
    if not os.path.exists(INPUT_DIR):
        print(f"Ошибка: входной каталог {INPUT_DIR} не существует")
        return
    
    # Находим все JSON файлы во входном каталоге
    json_files = []
    try:
        for file_name in os.listdir(INPUT_DIR):
            if file_name.endswith('.json'):
                json_files.append(os.path.join(INPUT_DIR, file_name))
    except Exception as e:
        print(f"Ошибка при чтении входного каталога {INPUT_DIR}: {e}")
        return
    
    if not json_files:
        print(f"Не найдено JSON файлов в каталоге {INPUT_DIR}")
        return
    
    print(f"Найдено {len(json_files)} JSON файлов для обработки")
    
    # Настраиваем Selenium драйвер
    driver = None
    try:
        driver = setup_selenium_driver()
        
        # Обрабатываем каждый JSON файл
        for json_file in json_files:
            process_json_file(json_file, driver)
            
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
    finally:
        if driver:
            driver.quit()
            print("Драйвер закрыт")
    
    print("\nОбработка завершена!")

if __name__ == "__main__":
    main()