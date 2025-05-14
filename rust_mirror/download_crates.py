import requests
import os
import json
import time
import logging
import signal
import sys

# Константа с конечным каталогом для скачивания
DOWNLOAD_DIR = "i://rust_crates_mirror"

# Файл со списком crates
CRATES_LIST_FILE = "filtered_crates.json"

# Файл для сохранения прогресса
PROGRESS_FILE = "progress.json"

# Сколько последних версий скачивать (например, 3 последние версии)
MAX_VERSIONS_TO_DOWNLOAD = 3

# Задержка между запросами (в секундах)
REQUEST_DELAY = 0

# Имя crate, с которого начать скачивание (если None, начнет с первого)
START_FROM_CRATE = 'fitimer'  # Например, "serde"

# Создаем каталог для скачивания, если он не существует
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Заголовки для запросов
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("download.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Флаг для graceful shutdown
shutdown_flag = False

def signal_handler(sig, frame):
    """Обработчик сигнала для graceful shutdown."""
    global shutdown_flag
    logging.info("Received interrupt signal (Ctrl+C). Shutting down gracefully...")
    shutdown_flag = True
    sys.exit(0)

# Регистрируем обработчик сигнала
signal.signal(signal.SIGINT, signal_handler)

def load_crates_list():
    """Загружает список crates из файла."""
    try:
        with open(CRATES_LIST_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load crates list: {e}")
        return []

def load_progress():
    """Загружает прогресс скачивания из файла."""
    try:
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}  # Если файл прогресса не существует, возвращаем пустой словарь
    except Exception as e:
        logging.error(f"Failed to load progress: {e}")
        return {}

def save_progress(progress):
    """Сохраняет прогресс скачивания в файл."""
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save progress: {e}")

def get_crate_versions(crate_name):
    """Получает список версий для crate."""
    if shutdown_flag:
        return []
    try:
        versions_url = f"https://crates.io/api/v1/crates/{crate_name}/versions"
        response = requests.get(versions_url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()['versions']
        else:
            logging.error(f"Failed to fetch versions for {crate_name}. Status code: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Error fetching versions for {crate_name}: {e}")
        return []

def download_crate_version(crate_name, version, progress):
    """Скачивает конкретную версию crate."""
    if shutdown_flag:
        return
    try:
        download_url = f"https://crates.io/api/v1/crates/{crate_name}/{version}/download"
        logging.info(f"Download URL for {crate_name} {version}: {download_url}")
        
        # Проверка, была ли версия уже скачана
        if crate_name in progress and version in progress[crate_name]:
            logging.info(f"Skipping {crate_name} {version}, already downloaded.")
            return
        
        # Проверка доступности ссылки с учетом перенаправлений
        response = requests.get(download_url, headers=HEADERS, stream=True)
        if response.status_code == 200:
            logging.info(f"Link is valid: {download_url}")
            # Создаем структуру каталогов, аналогичную crates.io
            crate_dir = os.path.join(DOWNLOAD_DIR, "crates", crate_name, version)
            os.makedirs(crate_dir, exist_ok=True)
            
            # Сохраняем файл с понятным именем
            file_path = os.path.join(crate_dir, f"{crate_name}-{version}.crate")
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Обновляем прогресс
            if crate_name not in progress:
                progress[crate_name] = []
            progress[crate_name].append(version)
            save_progress(progress)
            
            logging.info(f"Downloaded {crate_name} {version} to {file_path}")
        else:
            logging.error(f"Link is invalid: {download_url}. Status code: {response.status_code}")
    except Exception as e:
        logging.error(f"Error downloading {crate_name} {version}: {e}")

def download_crate(crate, progress):
    """Скачивает последние версии crate."""
    if shutdown_flag:
        return
    crate_name = crate['name']
    versions = get_crate_versions(crate_name)
    
    # Ограничиваем количество скачиваемых версий
    versions = versions[:MAX_VERSIONS_TO_DOWNLOAD]
    
    for version in versions:
        if shutdown_flag:
            break
        version_num = version['num']
        download_crate_version(crate_name, version_num, progress)
        time.sleep(REQUEST_DELAY)  # Задержка между запросами

def main():
    """Основная функция для скачивания crates."""
    crates = load_crates_list()
    if not crates:
        logging.error("No crates to download. Exiting.")
        return

    # Загружаем прогресс
    progress = load_progress()

    # Общее количество элементов
    total_crates = len(crates)
    logging.info(f"Total crates to download: {total_crates}")

    # Определяем индекс, с которого начать скачивание
    start_index = 0
    if START_FROM_CRATE:
        for i, crate in enumerate(crates):
            if crate['name'] == START_FROM_CRATE:
                start_index = i
                break

    for index, crate in enumerate(crates[start_index:], start=start_index + 1):
        if shutdown_flag:
            break
        logging.info(f"Downloading crate {index} of {total_crates}: {crate['name']}")
        download_crate(crate, progress)

if __name__ == "__main__":
    main()