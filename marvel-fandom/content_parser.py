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
INPUT_DIR = "marvel-fandom-en"  # Каталог с JSON файлами со списками
OUTPUT_DIR = "marvel-fandom-en/parsed_content"  # Выходной каталог
MAIN_CONTENT_SELECTOR = "body > div.main-container > div.resizable-container > div.page.has-right-rail > main"
BASE_URL = "https://marvel.fandom.com"
ERROR_LOG_FILE = "marvel-fandom-en/parsing_errors.log"  # Файл для лога ошибок

# Настройки времени паузы
SHORT_PAUSE_MIN = 10  # Минимальная пауза между запросами (секунды)
SHORT_PAUSE_MAX = 15  # Максимальная пауза между запросами (секунды)
LONG_PAUSE_MIN = 20   # Минимальная длинная пауза (секунды)
LONG_PAUSE_MAX = 35  # Максимальная длинная пауза (секунды)
PAGES_BEFORE_LONG_PAUSE = 10  # Количество страниц перед длинной паузой

def generate_safe_filename(title: str, index: int) -> str:
    """Сгенерировать безопасное имя файла из названия страницы."""
    import re
    
    if not title or not title.strip():
        return f"page_{index}_untitled"
    
    original_title = title
    
    # Заменяем проблемные символы на безопасные
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)  # Запрещенные символы Windows
    safe_title = re.sub(r'[\'"!@#$%^&*()+=\[\]{};:\'",.<>?/\\|`~]', '_', safe_title)  # Дополнительные символы
    safe_title = re.sub(r'\s+', '_', safe_title)  # Заменяем пробелы на подчеркивания
    safe_title = re.sub(r'_+', '_', safe_title)  # Убираем множественные подчеркивания
    safe_title = safe_title.strip('_')  # Убираем подчеркивания в начале и конце
    
    # Оставляем только безопасные символы
    safe_title = "".join(c for c in safe_title if c.isalnum() or c in ('-', '_')).rstrip()
    
    # Если после очистки ничего не осталось, используем индекс
    if not safe_title:
        safe_title = f"page_{index}"
    elif len(safe_title) < 3:
        safe_title = f"page_{index}_{safe_title}"
    
    # Ограничиваем длину
    safe_title = safe_title[:100]
    
    # Логируем, если имя сильно изменилось
    if safe_title != original_title.replace(' ', '_'):
        print(f"⚠️ Имя файла изменено: '{original_title[:50]}...' -> '{safe_title}'")
    
    return safe_title

def check_existing_files(title: str, index: int, output_subdir: str) -> tuple:
    """
    Проверить существует ли файл с данным названием в различных форматах.
    Возвращает кортеж (exists: bool, existing_filename: str or None, safe_filename: str, has_error: bool)
    """
    import re
    # Генерируем безопасное имя
    safe_filename = generate_safe_filename(title, index)
    safe_filepath = os.path.join(output_subdir, f"{safe_filename}.json")
    
    # Проверяем существование файла с безопасным именем
    if os.path.exists(safe_filepath):
        has_error = check_file_has_error(safe_filepath)
        return True, safe_filename, safe_filename, has_error
    
    # Проверяем существование файла с оригинальным именем (старый формат)
    old_safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    old_safe_title = old_safe_title.replace(' ', '_')[:100]
    old_filepath = os.path.join(output_subdir, f"{old_safe_title}.json")
    
    if os.path.exists(old_filepath):
        has_error = check_file_has_error(old_filepath)
        return True, old_safe_title, safe_filename, has_error
    
    # Проверяем другие возможные варианты имен
    # Вариант с заменой только основных запрещенных символов
    basic_safe = re.sub(r'[<>:"/\\|?*]', '_', title)
    basic_safe = basic_safe.replace(' ', '_')[:100]
    basic_filepath = os.path.join(output_subdir, f"{basic_safe}.json")
    
    if os.path.exists(basic_filepath):
        has_error = check_file_has_error(basic_filepath)
        return True, basic_safe, safe_filename, has_error
    
    return False, None, safe_filename, False

def check_file_has_error(filepath: str) -> bool:
    """Проверить, содержит ли файл ошибку."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = json.load(f)
        return 'error' in content
    except:
        return False

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
                # Для страниц-галерей и других специальных страниц
                page_title = soup.find("h1", id="firstHeading") or soup.find("h1", class_="page-header__title")
                title_text = page_title.get_text(strip=True) if page_title else "Unknown"
                
                # Проверяем, является ли это страницей-галереей
                if "/Gallery" in title_text or "Gallery" in title_text:
                    gallery_content = soup.find("div", class_="wikia-gallery")
                    if gallery_content:
                        return {
                            "title": title_text,
                            "url": "",
                            "main_content": "This is a gallery page with images",
                            "sections": [{"level": 2, "title": "Gallery", "content": "Image gallery content"}],
                            "infobox": {},
                            "categories": ["Gallery"],
                            "raw_html": str(soup.find("body"))[:500]
                        }
                
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
    
    # Секции статьи - улучшенная версия
    sections = main_content.find_all(["h2", "h3", "h4"])
    for section in sections:
        section_title = section.get_text(strip=True)
        section_data = {
            "level": int(section.name[1]),
            "title": section_title,
            "content": ""
        }
        
        # Специальная обработка для секции "Contents"
        if section_title.lower() == "contents":
            # Ищем оглавление внутри секции
            toc_links = section.find_next_sibling("ul") or section.find_next_sibling("div", class_="toc")
            if not toc_links:
                # Ищем внутри div с классом toc
                toc_div = main_content.find("div", class_="toc")
                if toc_div:
                    toc_links = toc_div
            
            if toc_links:
                toc_items = []
                links = toc_links.find_all("a")
                for link in links:
                    link_text = link.get_text(strip=True)
                    if link_text and not link_text.startswith('[') and len(link_text) > 2:
                        toc_items.append(link_text)
                if toc_items:
                    section_data["content"] = "\n".join(toc_items)
        
        # Специальная обработка для секции "First"
        elif section_title.lower() == "first":
            # Ищем информацию о первом появлении в различных местах
            first_info = section.find_next_sibling("div", class_="pi-smart-data-value")
            if not first_info:
                # Ищем в родительском контейнере
                parent_section = section.find_parent("section", class_="pi-smart-group")
                if parent_section:
                    first_info = parent_section.find("div", class_="pi-smart-data-value")
            
            if first_info:
                first_text = first_info.get_text(strip=True)
                if first_text:
                    section_data["content"] = first_text
        
        # Специальная обработка для секции "Links and References"
        elif "links" in section_title.lower() or "references" in section_title.lower():
            # Ищем ссылки и сноски
            ref_links = section.find_next_sibling("div", class_="mw-references-wrap")
            if ref_links:
                ref_items = []
                ref_items_elements = ref_links.find_all("span", class_="reference-text")
                for ref_item in ref_items_elements:
                    ref_text = ref_item.get_text(strip=True)
                    if ref_text:
                        ref_items.append(ref_text)
                if ref_items:
                    section_data["content"] = "\n".join(ref_items[:10])  # Ограничиваем количество сносок
        
        # Для всех других секций используем стандартную обработку
        else:
            # Собираем контент до следующего заголовка
            current = section.find_next_sibling()
            content_parts = []  # Инициализируем переменную здесь
            while current:
                # Проверяем, является ли текущий элемент заголовком
                if current.name in ["h2", "h3", "h4"]:
                    break
                
                # Проверяем, что current не None и имеет атрибут name
                if not hasattr(current, 'name'):
                    # Безопасно переходим к следующему элементу
                    next_sibling = current.find_next_sibling()
                    if next_sibling is None:
                        break
                    current = next_sibling
                    continue
                if current.name == "p":
                    # Абзацы
                    text = current.get_text(strip=True)
                    if text:
                        content_parts.append(text)
                elif current.name in ["ul", "ol"]:
                    # Списки
                    items = [li.get_text(strip=True) for li in current.find_all("li")]
                    if items:
                        content_parts.extend(items)
                elif current.name == "div":
                    # Дивы с контентом - улучшенная обработка
                    # Проверяем различные классы дивов, которые могут содержать контент
                    div_classes = current.get('class', [])
                    div_text = current.get_text(strip=True)
                    
                    # Специальная обработка для различных типов div'ов
                    if 'mw-collapsible-content' in div_classes:
                        # Раскрывающийся контент
                        if div_text:
                            content_parts.append(div_text)
                    elif 'marvel_database_section' in div_classes:
                        # Секции Marvel Database
                        if div_text:
                            content_parts.append(div_text)
                    elif 'pi-smart-group-body' in div_classes:
                        # Инфобокс группы
                        if div_text:
                            content_parts.append(div_text)
                    elif 'thumbcaption' in div_classes:
                        # Подписи к изображениям
                        if div_text:
                            content_parts.append(f"Изображение: {div_text}")
                    else:
                        # Обычные дивы
                        if div_text and len(div_text) > 10:  # Фильтруем очень короткий текст
                            content_parts.append(div_text)
                elif current.name == "table":
                    # Таблицы
                    rows = []
                    for row in current.find_all("tr"):
                        cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
                        if cells:
                            rows.append(" | ".join(cells))
                    if rows:
                        content_parts.append("Таблица:\n" + "\n".join(rows))
                elif current.name == "blockquote":
                    # Цитаты
                    text = current.get_text(strip=True)
                    if text:
                        content_parts.append(f"Цитата: {text}")
                elif current.name == "dl":
                    # Списки определений
                    terms = []
                    for dt in current.find_all("dt"):
                        term = dt.get_text(strip=True)
                        dd = dt.find_next_sibling("dd")
                        if dd:
                            definition = dd.get_text(strip=True)
                            terms.append(f"{term}: {definition}")
                    if terms:
                        content_parts.extend(terms)
                elif current.name == "pre":
                    # Преформатированный текст
                    text = current.get_text(strip=True)
                    if text:
                        content_parts.append(f"Код/Преформатированный текст: {text}")
                elif current.name == "figure":
                    # Изображения с подписями
                    caption = current.find("figcaption")
                    if caption:
                        caption_text = caption.get_text(strip=True)
                        if caption_text:
                            content_parts.append(f"Изображение: {caption_text}")
                elif current.name == "span":
                    # Спаны с классами, которые могут содержать важный контент
                    span_classes = current.get('class', [])
                    span_text = current.get_text(strip=True)
                    if span_text and ('mw-page-title-main' in span_classes or 'mw-headline' in span_classes):
                        content_parts.append(span_text)
                
                # Безопасно переходим к следующему элементу
                next_sibling = current.find_next_sibling()
                if next_sibling is None:
                    break
                current = next_sibling
            
            section_data["content"] = "\n".join(content_parts) if content_parts else ""
            if current.name == "p":
                # Абзацы
                text = current.get_text(strip=True)
                if text:
                    content_parts.append(text)
            elif current.name in ["ul", "ol"]:
                # Списки
                items = [li.get_text(strip=True) for li in current.find_all("li")]
                if items:
                    content_parts.extend(items)
            elif current.name == "div":
                # Дивы с контентом - улучшенная обработка
                # Проверяем различные классы дивов, которые могут содержать контент
                div_classes = current.get('class', [])
                div_text = current.get_text(strip=True)
                
                # Специальная обработка для различных типов div'ов
                if 'mw-collapsible-content' in div_classes:
                    # Раскрывающийся контент
                    if div_text:
                        content_parts.append(div_text)
                elif 'marvel_database_section' in div_classes:
                    # Секции Marvel Database
                    if div_text:
                        content_parts.append(div_text)
                elif 'pi-smart-group-body' in div_classes:
                    # Инфобокс группы
                    if div_text:
                        content_parts.append(div_text)
                elif 'thumbcaption' in div_classes:
                    # Подписи к изображениям
                    if div_text:
                        content_parts.append(f"Изображение: {div_text}")
                else:
                    # Обычные дивы
                    if div_text and len(div_text) > 10:  # Фильтруем очень короткий текст
                        content_parts.append(div_text)
            elif current.name == "table":
                # Таблицы
                rows = []
                for row in current.find_all("tr"):
                    cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
                    if cells:
                        rows.append(" | ".join(cells))
                if rows:
                    content_parts.append("Таблица:\n" + "\n".join(rows))
            elif current.name == "blockquote":
                # Цитаты
                text = current.get_text(strip=True)
                if text:
                    content_parts.append(f"Цитата: {text}")
            elif current.name == "dl":
                # Списки определений
                terms = []
                for dt in current.find_all("dt"):
                    term = dt.get_text(strip=True)
                    dd = dt.find_next_sibling("dd")
                    if dd:
                        definition = dd.get_text(strip=True)
                        terms.append(f"{term}: {definition}")
                if terms:
                    content_parts.extend(terms)
            elif current.name == "pre":
                # Преформатированный текст
                text = current.get_text(strip=True)
                if text:
                    content_parts.append(f"Код/Преформатированный текст: {text}")
            elif current.name == "figure":
                # Изображения с подписями
                caption = current.find("figcaption")
                if caption:
                    caption_text = caption.get_text(strip=True)
                    if caption_text:
                        content_parts.append(f"Изображение: {caption_text}")
            elif current.name == "span":
                # Спаны с классами, которые могут содержать важный контент
                span_classes = current.get('class', [])
                span_text = current.get_text(strip=True)
                if span_text and ('mw-page-title-main' in span_classes or 'mw-headline' in span_classes):
                    content_parts.append(span_text)
            
            current = current.find_next_sibling()
        
        section_data["content"] = "\n".join(content_parts)
        content_data["sections"].append(section_data)
    
    # Основной текст (первые несколько абзацев) - улучшенная версия
    main_content_parts = []
    
    # Сначала ищем основной текст в различных контейнерах
    # Проверяем div с классом marvel_database_section
    main_sections = main_content.find_all("div", class_="marvel_database_section")
    for section in main_sections:
        section_text = section.get_text(strip=True)
        if section_text:
            main_content_parts.append(section_text)
    
    # Если не нашли специальные секции, используем обычные абзацы
    if not main_content_parts:
        paragraphs = main_content.find_all("p", limit=15)
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and len(text) > 10:  # Фильтруем очень короткий текст
                main_content_parts.append(text)
    
    # Также ищем контент в раскрывающихся блоках
    collapsible_blocks = main_content.find_all("div", class_="mw-collapsible-content")
    for block in collapsible_blocks:
        block_text = block.get_text(strip=True)
        if block_text and len(block_text) > 20:
            main_content_parts.append(f"[Раскрывающийся контент]: {block_text}")
    
    # Ищем контент в figure с подписями
    figures = main_content.find_all("figure", class_="thumb")
    for figure in figures:
        caption = figure.find("figcaption")
        if caption:
            caption_text = caption.get_text(strip=True)
            if caption_text:
                main_content_parts.append(f"[Изображение]: {caption_text}")
    
    content_data["main_content"] = "\n".join(main_content_parts)
    
    # Категории - ищем во всем документе, а не только в main_content
    categories = []
    
    # Ищем категории на русском языке
    russian_category_links = soup.find_all("a", href=lambda x: x and "/wiki/Категория:" in x)
    categories.extend([cat.get_text(strip=True) for cat in russian_category_links])
    
    # Ищем категории на английском языке
    english_category_links = soup.find_all("a", href=lambda x: x and "/wiki/Category:" in x)
    categories.extend([cat.get_text(strip=True) for cat in english_category_links])
    
    # Убираем дубликаты и пустые значения
    content_data["categories"] = list(set([cat for cat in categories if cat]))
    
    return content_data

def parse_infobox(infobox) -> dict:
    """Парсинг инфобокса с информацией о персонаже."""
    infobox_data = {}
    
    # Заголовок инфобокса
    title_elem = infobox.find("h2", class_="pi-item pi-title")
    if title_elem:
        infobox_data["name"] = title_elem.get_text(strip=True)
    
    # Изображение инфобокса
    image_elem = infobox.find("figure", class_="pi-item pi-image")
    if image_elem:
        img = image_elem.find("img")
        if img and img.get("src"):
            infobox_data["image"] = img.get("src")
    
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
                else:
                    # Обработка элементов без явного лейбла (например, "Занятие:", "Организации:")
                    value_div = item.find("div", class_="pi-data-value")
                    if value_div:
                        text = value_div.get_text(strip=True)
                        if ":" in text:
                            parts = text.split(":", 1)
                            key = parts[0].strip()
                            value = parts[1].strip()
                            infobox_data[group_name][key] = value
    
    # Одиночные элементы данных (не в группах)
    standalone_items = infobox.find_all("div", class_="pi-item pi-data")
    for item in standalone_items:
        if not item.find_parent("section", class_="pi-item pi-group"):
            label = item.find("h3", class_="pi-data-label")
            value = item.find("div", class_="pi-data-value")
            if label and value:
                key = label.get_text(strip=True).rstrip(":")
                infobox_data[key] = value.get_text(strip=True)
    
    return infobox_data

def log_error(url: str, title: str, error_message: str):
    """Записать ошибку в лог файл."""
    try:
        os.makedirs(os.path.dirname(ERROR_LOG_FILE), exist_ok=True)
        with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {title} ({url}): {error_message}\n")
        print(f"✗ Ошибка записана в лог: {title}")
    except Exception as e:
        print(f"✗ Ошибка при записи в лог файл: {e}")

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

def process_json_file(json_file_path: str, driver) -> int:
    """Обработать один JSON файл со списком ссылок. Возвращает количество обработанных страниц."""
    print(f"\nОбработка файла: {json_file_path}")
    processed_count = 0
    
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
        
        # Проверяем существование файла в различных форматах имен
        exists, existing_filename, safe_filename, has_error = check_existing_files(title, i, output_subdir)
        
        if exists and not has_error:
            print(f"Пропуск {title}: уже обработано как '{existing_filename}'")
            continue
        elif exists and has_error:
            print(f"Перезапись {title}: файл содержит ошибку")
        
        # Используем безопасное имя для нового файла
        output_file = os.path.join(output_subdir, f"{safe_filename}.json")
        
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
                
                # Проверяем, что файл действительно создан
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    percentage = (i + 1) / len(links_data) * 100
                    print(f"✓ Сохранено: {title} ({i+1}/{len(links_data)}) - {percentage:.1f}% - {file_size} байт")
                else:
                    print(f"✗ Ошибка: файл не был создан: {output_file}")
                    raise Exception(f"Файл не был создан: {output_file}")
                    
            except Exception as e:
                print(f"✗ Ошибка при сохранении файла {output_file}: {e}")
                raise
            
            processed_count += 1
            # Случайная задержка между запросами
            time.sleep(random.uniform(SHORT_PAUSE_MIN, SHORT_PAUSE_MAX))
            
        except Exception as e:
            print(f"✗ Ошибка при обработке {title}: {e}")
            # Записываем ошибку в лог файл
            log_error(url, title, str(e))
        
        # Каждые N страниц делаем длинную паузу
        if (i + 1) % PAGES_BEFORE_LONG_PAUSE == 0:
            print(f"Длинная пауза после {i + 1} страниц...")
            time.sleep(random.uniform(LONG_PAUSE_MIN, LONG_PAUSE_MAX))
    
    return processed_count

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
    total_expected = 0
    total_processed = 0
    
    try:
        driver = setup_selenium_driver()
        
        # Обрабатываем каждый JSON файл
        for json_file in json_files:
            processed_count = process_json_file(json_file, driver)
            total_processed += processed_count
            
            # Подсчитываем общее количество ожидаемых файлов
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    links_data = json.load(f)
                    if isinstance(links_data, list):
                        total_expected += len(links_data)
            except:
                pass
            
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
    finally:
        if driver:
            driver.quit()
            print("Драйвер закрыт")
    
    # Подсчитываем фактическое количество файлов
    actual_files = 0
    for json_file in json_files:
        file_name = Path(json_file).stem
        output_subdir = os.path.join(OUTPUT_DIR, file_name)
        if os.path.exists(output_subdir):
            files_in_dir = [f for f in os.listdir(output_subdir) if f.endswith('.json')]
            actual_files += len(files_in_dir)
    
    print(f"\n=== СТАТИСТИКА ===")
    print(f"Ожидаемое количество файлов: {total_expected}")
    print(f"Обработано страниц: {total_processed}")
    print(f"Фактическое количество файлов: {actual_files}")
    print(f"Разница: {total_expected - actual_files}")
    
    if total_expected != actual_files:
        print(f"⚠️ Внимание: разница в {total_expected - actual_files} файлах!")
    else:
        print("✓ Все файлы успешно сохранены!")
    
    print("\nОбработка завершена!")

if __name__ == "__main__":
    main()