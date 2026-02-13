"""
YouTube Transcript Extractor - Полная версия

Скрипт для автоматического извлечения транскрипций видео с YouTube.
Открывает файл со списком ссылок, заходит на каждую страницу видео,
раскрывает блок описания, нажимает "Показать текст видео", скрывает
временные метки и сохраняет чистый текст транскрипции в отдельные файлы.

Особенности:
1. Первое открытие YouTube с задержкой 7 секунд для ручного принятия куки
2. Автоматическое раскрытие блока описания (кнопка "ещё")
3. Поиск и клик по кнопке "Показать текст видео"
4. Клик на кнопку "Ещё" (троеточие) в блоке транскрипции
5. Выбор пункта "Показать или скрыть временные метки"
6. Извлечение текста транскрипции без таймкодов
7. Сохранение в файлы с именами на основе заголовков видео
8. Обработка случаев, когда транскрипция недоступна
9. Детальное логирование процесса
10. Очистка текста от остатков таймкодов

Примечание: Транскрипция может быть недоступна для некоторых видео
по следующим причинам:
- Автор отключил транскрипцию
- Требуется авторизация в аккаунте Google
- Транскрипция загружается через отдельный API
- Необходимо принять дополнительные соглашения

Использование:
1. Поместите ссылки на видео YouTube в файл (по одной на строку)
2. Укажите путь к файлу в переменной YOUTUBE_LINKS_FILE
3. Запустите скрипт: python extract_text_complete.py
4. При первом запуске примите куки и соглашения в браузере
5. Скрипт автоматически обработает все ссылки

Результат:
- Транскрипции сохраняются в папке transcripts/
- Имена файлов формируются из заголовков видео
- Если транскрипция недоступна, сохраняется информация об этом
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
import time
import re
import os

# ===== НАСТРОЙКИ =====
YOUTUBE_LINKS_FILE = r"c1mami__Механическое движение.txt"   # одна ссылка на строку
OUTPUT_DIR = r"transcripts"        # куда сохранять тексты
FIRST_OPEN_DELAY = 7                             # сек. на ручное принятие куки
MAX_TITLE_LEN = 30                               # ограничение длины имени файла
MAX_RETRIES = 2                                  # количество попыток при ошибках
TIMEOUT = 20                                     # таймаут ожидания элементов (сек)

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def sanitize_filename(name: str, max_len: int = 80) -> str:
    """Удаляем запрещённые для файловой системы символы и режем длину."""
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    name = name.strip()
    if len(name) > max_len:
        name = name[:max_len].rstrip(' ._')
    if not name:
        name = "video"
    return name

def wait_and_click(driver, by, selector, timeout=TIMEOUT):
    """Ждём появления элемента и кликаем по нему."""
    el = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, selector))
    )
    el.click()
    return el

def safe_find_element(driver, by, selector, timeout=TIMEOUT):
    """Безопасный поиск элемента с ожиданием."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        return element
    except:
        return None

def get_transcript_text(driver, url) -> str:
    """
    Пытается открыть «Показать текст видео», скрыть временные метки и вернуть текст расшифровки.
    Возвращает текст транскрипции или пустую строку, если транскрипция недоступна.
    """
    print(f"  Попытка получить транскрипцию для {url}")
    
    try:
        # 1. Прокручиваем страницу вниз, чтобы элементы были видны
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(1)
        
        # 2. Кликаем на кнопку "ещё" для раскрытия описания
        try:
            expand_button = driver.find_element(By.CSS_SELECTOR, "tp-yt-paper-button#expand")
            driver.execute_script("arguments[0].click();", expand_button)
            print("    ✅ Кликнули на 'ещё' для раскрытия описания")
            time.sleep(2)
        except Exception as e:
            print(f"    ⚠️  Не удалось кликнуть на 'ещё' для описания: {e}")
        
        # 3. Ищем кнопку "Показать текст видео" разными способами
        show_text_buttons = []
        
        # Способ 1: По тексту кнопки
        show_text_buttons.extend(driver.find_elements(By.XPATH, "//button[contains(., 'Показать текст видео')]"))
        
        # Способ 2: По классу и тексту
        show_text_buttons.extend(driver.find_elements(By.XPATH, "//yt-button-shape//button[.//span[contains(., 'Показать текст видео')]]"))
        
        # Способ 3: По атрибуту aria-label
        show_text_buttons.extend(driver.find_elements(By.XPATH, "//button[@aria-label='Показать текст видео']"))
        
        print(f"    Найдено кнопок 'Показать текст видео': {len(show_text_buttons)}")
        
        if not show_text_buttons:
            print("    ❌ Кнопка 'Показать текст видео' не найдена")
            return ""
        
        # 4. Кликаем на первую найденную кнопку
        try:
            driver.execute_script("arguments[0].click();", show_text_buttons[0])
            print("    ✅ Кликнули на 'Показать текст видео'")
            time.sleep(3)  # Даем время для загрузки транскрипции
        except Exception as e:
            print(f"    ❌ Ошибка при клике на кнопку: {e}")
            return ""
        
        # 5. Пытаемся скрыть временные метки
        try:
            # Ищем кнопку "Ещё" (троеточие) в блоке транскрипции
            more_buttons = driver.find_elements(By.XPATH, "//button[@aria-label='Ещё' or contains(@class, 'yt-icon-button')]")
            
            for button in more_buttons:
                try:
                    # Проверяем, находится ли кнопка в блоке транскрипции
                    parent = button.find_element(By.XPATH, "./ancestor::ytd-transcript-renderer | ./ancestor::ytd-engagement-panel-section-list-renderer")
                    if parent:
                        driver.execute_script("arguments[0].click();", button)
                        print("    ✅ Кликнули на кнопку 'Ещё' (троеточие)")
                        time.sleep(1)
                        
                        # Ищем пункт меню "Показать или скрыть временные метки"
                        menu_items = driver.find_elements(By.XPATH, "//yt-formatted-string[contains(., 'Показать или скрыть временные метки') or contains(., 'Скрыть временные метки') or contains(., 'Hide timestamps')]")
                        
                        if menu_items:
                            driver.execute_script("arguments[0].click();", menu_items[0])
                            print("    ✅ Кликнули на 'Показать или скрыть временные метки'")
                            time.sleep(2)  # Даем время для скрытия таймкодов
                            break
                except:
                    continue
        except Exception as e:
            print(f"    ⚠️  Не удалось скрыть временные метки: {e}")
        
        # 6. Ждём появления транскрипции и извлекаем текст
        transcript_text = ""
        
        # Способ 1: Ищем ytd-transcript-renderer
        transcript_renderer = safe_find_element(driver, By.TAG_NAME, "ytd-transcript-renderer")
        if transcript_renderer and transcript_renderer.text.strip():
            transcript_text = transcript_renderer.text.strip()
            print(f"    ✅ Найден ytd-transcript-renderer, длина текста: {len(transcript_text)}")
        
        # Способ 2: Ищем yt-formatted-string.segment-text (без таймкодов)
        if not transcript_text:
            segment_texts = driver.find_elements(By.CSS_SELECTOR, "yt-formatted-string.segment-text")
            if segment_texts:
                lines = [el.text.strip() for el in segment_texts if el.text.strip()]
                transcript_text = "\n".join(lines)
                print(f"    ✅ Найдено {len(segment_texts)} segment-text, длина текста: {len(transcript_text)}")
        
        # Способ 3: Ищем текст в engagement panel
        if not transcript_text:
            try:
                engagement_panels = driver.find_elements(By.CSS_SELECTOR, "ytd-engagement-panel-section-list-renderer")
                for panel in engagement_panels:
                    if panel.is_displayed():
                        text = panel.text.strip()
                        if text and len(text) > 100:  # Достаточно длинный текст
                            transcript_text = text
                            print(f"    ✅ Найден текст в engagement panel, длина: {len(transcript_text)}")
                            break
            except Exception as e:
                print(f"    ⚠️  Ошибка при поиске в engagement panel: {e}")
        
        # 7. Очищаем текст от возможных остатков таймкодов
        if transcript_text:
            # Удаляем строки, которые выглядят как таймкоды (например, "0:00", "1:23:45")
            lines = transcript_text.split('\n')
            cleaned_lines = []
            for line in lines:
                # Пропускаем строки, которые содержат только таймкод
                if re.match(r'^\d+:\d+(:\d+)?$', line.strip()):
                    continue
                # Пропускаем строки, которые начинаются с таймкода и пробела
                if re.match(r'^\d+:\d+(:\d+)?\s+', line):
                    # Удаляем таймкод из начала строки
                    line = re.sub(r'^\d+:\d+(:\d+)?\s+', '', line)
                cleaned_lines.append(line.strip())
            
            transcript_text = '\n'.join([line for line in cleaned_lines if line])
            print(f"    ✅ Транскрипция получена и очищена от таймкодов ({len(transcript_text)} символов)")
            return transcript_text
        else:
            print("    ❌ Текст транскрипции не найден после клика")
            return ""
            
    except Exception as e:
        print(f"    ❌ Ошибка при получении транскрипции: {e}")
        return ""

def process_video(driver, url, idx, total):
    """Обрабатывает одно видео."""
    print(f"\n[{idx}/{total}] Обработка: {url}")
    
    for attempt in range(MAX_RETRIES):
        try:
            driver.get(url)
            
            # Ждём загрузки страницы и заголовка
            try:
                # Пробуем разные селекторы для заголовка
                title_el = None
                selectors = [
                    "#title > h1 yt-formatted-string",  # Основной селектор
                    "h1.style-scope ytd-watch-metadata yt-formatted-string",  # Альтернативный
                    "ytd-watch-metadata h1 yt-formatted-string",  # Еще один вариант
                    "h1.title yt-formatted-string",  # Старый селектор
                ]
                
                for selector in selectors:
                    try:
                        title_el = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        if title_el and title_el.text.strip():
                            break
                    except:
                        continue
                
                if not title_el or not title_el.text.strip():
                    raise Exception("Не удалось найти заголовок видео")
                    
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"  ⚠️  Попытка {attempt + 1}: Не удалось загрузить страницу, повторяем...")
                    time.sleep(2)
                    continue
                else:
                    print(f"  ❌ Не удалось загрузить страницу после {MAX_RETRIES} попыток: {e}")
                    return None, None
            
            # Получаем заголовок
            try:
                title = title_el.text.strip()
                print(f"  Заголовок видео: {title[:50]}..." if len(title) > 50 else f"  Заголовок видео: {title}")
                filename = sanitize_filename(title, MAX_TITLE_LEN) + ".txt"
            except Exception as e:
                print(f"  ⚠️  Не удалось получить заголовок: {e}")
                filename = f"video_{idx}.txt"
                title = f"Видео {idx}"
            
            # Получаем транскрипцию
            transcript = get_transcript_text(driver, url)
            
            return filename, transcript
            
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  ⚠️  Попытка {attempt + 1} не удалась: {e}, повторяем...")
                time.sleep(2)
            else:
                print(f"  ❌ Все попытки не удались: {e}")
                return None, None
    
    return None, None

# ===== ОСНОВНОЙ КОД =====

def main():
    """Основная функция скрипта."""
    print("=" * 70)
    print("YouTube Transcript Extractor - Полная версия")
    print("=" * 70)
    print("Функции:")
    print("1. Раскрытие блока описания (кнопка 'ещё')")
    print("2. Клик на 'Показать текст видео'")
    print("3. Скрытие временных меток через меню 'Ещё'")
    print("4. Извлечение чистого текста транскрипции")
    print("5. Сохранение в отдельные файлы")
    print("=" * 70)
    
    # Проверяем существование файла со ссылками
    links_path = Path(YOUTUBE_LINKS_FILE)
    if not links_path.exists():
        print(f"❌ Файл со ссылками не найден: {YOUTUBE_LINKS_FILE}")
        print(f"   Текущая рабочая директория: {os.getcwd()}")
        print(f"   Проверьте наличие файла: {links_path.absolute()}")
        return
    
    # Читаем ссылки
    try:
        links = [line.strip() for line in links_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception as e:
        print(f"❌ Ошибка при чтении файла со ссылками: {e}")
        return
    
    if not links:
        print("❌ Файл со ссылками пуст")
        return
    
    print(f"Найдено ссылок: {len(links)}")
    
    # Готовим папку для вывода
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Папка для сохранения: {OUTPUT_DIR}")
    
    # Настройки браузера
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # chrome_options.add_argument("--headless=new")  # куки надо ручками принять, поэтому, скорее всего, без headless
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except Exception as e:
        print(f"❌ Ошибка при запуске браузера: {e}")
        print("   Убедитесь, что ChromeDriver установлен и доступен в PATH")
        print("   Скачать можно с: https://chromedriver.chromium.org/")
        return
    
    try:
        # Первое открытие YouTube для ручного принятия куки
        print(f"\n{'='*70}")
        print("ПЕРВОЕ ОТКРЫТИЕ YOUTUBE ДЛЯ ПРИНЯТИЯ КУКИ")
        print(f"{'='*70}")
        print(f"Ожидание {FIRST_OPEN_DELAY} сек. для ручного принятия куки...")
        print("ВАЖНО: Пожалуйста, примите куки и соглашения в открывшемся браузере")
        print("После этого скрипт продолжит работу автоматически")
        print(f"{'='*70}")
        
        driver.get("https://www.youtube.com/")
        time.sleep(FIRST_OPEN_DELAY)
        
        successful = 0
        failed = 0
        no_transcript = 0
        
        # Обрабатываем каждое видео
        for idx, url in enumerate(links, start=1):
            filename, transcript = process_video(driver, url, idx, len(links))
            
            if filename is None:
                failed += 1
                continue
            
            out_path = Path(OUTPUT_DIR) / filename
            
            if transcript:
                # Сохраняем транскрипцию
                try:
                    out_path.write_text(transcript, encoding="utf-8")
                    print(f"  ✅ Сохранено: {out_path} ({len(transcript)} символов)")
                    successful += 1
                except Exception as e:
                    print(f"  ❌ Ошибка при сохранении файла: {e}")
                    failed += 1
            else:
                # Сохраняем информацию о недоступности транскрипции
                try:
                    error_msg = f"""Транскрипция недоступна для видео

URL: {url}
Заголовок: {filename.replace('.txt', '')}
Время проверки: {time.strftime('%Y-%m-%d %H:%M:%S')}

Возможные причины:
1. Транскрипция отключена автором видео
2. Требуется авторизация в аккаунте Google
3. Транскрипция загружается через отдельный API
4. Необходимо принять дополнительные соглашения
5. Видео не имеет транскрипции

Для ручной проверки откройте видео в браузере и проверьте наличие кнопки
"Показать текст видео" под описанием видео.
"""
                    out_path.write_text(error_msg, encoding="utf-8")
                    print(f"  ⚠️  Транскрипция недоступна, сохранена информация: {out_path}")
                    no_transcript += 1
                except Exception as e:
                    print(f"  ❌ Ошибка при сохранении информации: {e}")
                    failed += 1
        
        # Итоговая статистика
        print(f"\n{'='*70}")
        print("ОБРАБОТКА ЗАВЕРШЕНА")
        print(f"{'='*70}")
        print(f"Всего видео: {len(links)}")
        print(f"Успешно извлечено транскрипций: {successful}")
        print(f"Транскрипция недоступна: {no_transcript}")
        print(f"Ошибки обработки: {failed}")
        
        if no_transcript > 0:
            print(f"\nПричины недоступности транскрипции:")
            print("1. Транскрипция может быть отключена автором видео")
            print("2. Может потребоваться авторизация в аккаунте Google")
            print("3. Транскрипция может загружаться через отдельный API")
            print("4. Возможно, нужно принять дополнительные соглашения")
            print(f"\nИнформация о недоступных транскрипциях сохранена в папке: {OUTPUT_DIR}")
        
        print(f"\nВсе файлы сохранены в папке: {OUTPUT_DIR}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Обработка прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
    finally:
        print("\nЗакрытие браузера...")
        driver.quit()
        print("Браузер закрыт")

if __name__ == "__main__":
    main()