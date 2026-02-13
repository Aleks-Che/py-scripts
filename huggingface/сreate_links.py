from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

# --- НАСТРОЙКИ ---
HUGGINGFACE_BASE_URL = "https://huggingface.co"
MODEL_REPO = "inferencerlabs/GLM-5-MLX-4.8bit"
SUBFOLDERS = ["Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"]  # несколько подкаталогов
# SUBFOLDERS = []  # если не нужен подкаталог, оставь пустым: SUBFOLDERS = []
# SUBFOLDERS = ["Q4_K_M"]  # один подкаталог
# SUBFOLDERS = ["", "Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"]  # несколько подкаталогов с корневым
# DOWNLOAD_ALL = False 

DOWNLOAD_ALL = True # создает ссылки на все файлы во всех подкаталогах, игнорируя SUBFOLDERS
OUTPUT_FILE = "download_links.txt"

def get_download_links(model_repo, subfolder=""):
    if subfolder:
        url = f"{HUGGINGFACE_BASE_URL}/{model_repo}/tree/main/{subfolder}"
    else:
        url = f"{HUGGINGFACE_BASE_URL}/{model_repo}/tree/main"
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    time.sleep(2)

    # Нажимаем кнопку "Load more files" пока она есть
    max_clicks = 50  # защита от бесконечного цикла
    for _ in range(max_clicks):
        try:
            # Ищем кнопку по тексту (используем XPath)
            load_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Load more files')]")
            # Прокручиваем к кнопке, чтобы она стала кликабельной
            driver.execute_script("arguments[0].scrollIntoView();", load_more_button)
            time.sleep(0.5)
            load_more_button.click()
            time.sleep(2)  # Ждем загрузки новых файлов
        except Exception:
            # Кнопка не найдена, значит все файлы загружены
            break

    download_links = []
    file_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="resolve/main"]')
    for el in file_elements:
        file_href = el.get_attribute("href")
        if file_href:
            if "?download=true" not in file_href:
                file_href += "?download=true"
            download_links.append(file_href)
    driver.quit()
    return download_links

def save_links_to_file(links, filename):
    with open(filename, "w", encoding="utf-8") as f:
        for link in links:
            f.write(link + "\n")

def get_all_subfolders(model_repo):
    """Возвращает список всех подкаталогов в корне репозитория (включая пустую строку для корня)."""
    url = f"{HUGGINGFACE_BASE_URL}/{model_repo}/tree/main"
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    time.sleep(2)
    
    # Нажимаем кнопку "Load more files" пока она есть (чтобы загрузить все подкаталоги)
    max_clicks = 50
    for _ in range(max_clicks):
        try:
            load_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Load more files')]")
            driver.execute_script("arguments[0].scrollIntoView();", load_more_button)
            time.sleep(0.5)
            load_more_button.click()
            time.sleep(2)
        except Exception:
            break
    
    # Ищем ссылки на подкаталоги (элементы <a> с href, содержащим 'tree/main/')
    # Исключаем ссылки на файлы (содержащие 'resolve/main')
    subfolders = []
    all_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="tree/main/"]')
    for link in all_links:
        href = link.get_attribute("href")
        if href and "resolve/main" not in href:
            # Извлекаем часть после tree/main/
            prefix = f"{HUGGINGFACE_BASE_URL}/{model_repo}/tree/main/"
            if href.startswith(prefix):
                subfolder = href[len(prefix):].rstrip('/')
                # Если subfolder не пустой и ещё не добавлен
                if subfolder and subfolder not in subfolders:
                    subfolders.append(subfolder)
    
    driver.quit()
    # Добавляем пустую строку для корня
    subfolders.insert(0, "")
    return subfolders

if __name__ == "__main__":
    all_links = []
    
    if DOWNLOAD_ALL:
        print("Режим 'скачать всё': получение списка всех подкаталогов...")
        subfolders_to_process = get_all_subfolders(MODEL_REPO)
        print(f"Найдено подкаталогов (включая корень): {len(subfolders_to_process)}")
    else:
        # Если SUBFOLDERS пустой список, обрабатываем корень (пустая строка)
        if not SUBFOLDERS:
            subfolders_to_process = [""]
        else:
            subfolders_to_process = SUBFOLDERS
    
    for subfolder in subfolders_to_process:
        print(f"Обработка подкаталога: '{subfolder if subfolder else 'корень'}'")
        links = get_download_links(MODEL_REPO, subfolder)
        all_links.extend(links)
        print(f"  найдено ссылок: {len(links)}")
    
    save_links_to_file(all_links, OUTPUT_FILE)
    print(f"Всего ссылок сохранено в файл {OUTPUT_FILE}: {len(all_links)}")
