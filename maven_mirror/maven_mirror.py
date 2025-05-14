import os
import requests
import json
import time

# Базовый URL Maven Central
BASE_URL = "https://repo1.maven.org/maven2/"
DEPENDENCIES_FILE = "updated_dependencies.json"
# Директория для сохранения артефактов
DOWNLOAD_DIR = "L://maven_mirror"

# Количество попыток скачивания
MAX_RETRIES = 3

# Задержка между попытками (в секундах)
RETRY_DELAY = 5

# Индекс артефакта, с которого начинать скачивание (начиная с 0)
START_ARTIFACT_INDEX = 0  # Измените это значение на нужное

def sanitize_filename(filename):
    """Заменяет недопустимые символы в именах файлов на допустимые."""
    invalid_chars = ':*?"<>|'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def sanitize_path(path):
    """Заменяет недопустимые символы в пути."""
    return sanitize_filename(path).replace('"', '')

def file_exists(url):
    """Проверяет, существует ли файл по указанному URL."""
    try:
        response = requests.head(url)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def get_file_size(url):
    """Возвращает размер файла на сервере."""
    try:
        response = requests.head(url)
        if response.status_code == 200:
            return int(response.headers.get("Content-Length", 0))
        return 0
    except requests.exceptions.RequestException:
        return 0

def download_file(url, path):
    """Скачивает файл по URL и сохраняет его в указанный путь с поддержкой продолжения."""
    # Санитизируем путь перед созданием директорий
    sanitized_path = sanitize_path(path)
    os.makedirs(os.path.dirname(sanitized_path), exist_ok=True)
    
    # Проверяем, существует ли файл и его размер
    if os.path.exists(sanitized_path):
        downloaded_size = os.path.getsize(sanitized_path)
        file_size = get_file_size(url)
        if downloaded_size == file_size:
            print(f"Файл уже скачан: {url}")
            return  # Файл уже полностью скачан
    else:
        downloaded_size = 0

    # Устанавливаем заголовок Range для продолжения загрузки
    headers = {"Range": f"bytes={downloaded_size}-"} if downloaded_size > 0 else {}

    for attempt in range(MAX_RETRIES):
        try:
            with requests.get(url, headers=headers, stream=True) as r:
                r.raise_for_status()
                # Проверяем, поддерживает ли сервер продолжение загрузки
                if r.status_code == 206:  # 206 - Partial Content
                    print(f"Продолжение загрузки: {url} (с {downloaded_size} байт)")
                    mode = "ab"  # Дописываем в конец файла
                else:
                    print(f"Начало загрузки: {url}")
                    mode = "wb"  # Перезаписываем файл

                with open(sanitized_path, mode) as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return  # Успешное скачивание
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при скачивании (попытка {attempt + 1} из {MAX_RETRIES}): {url}")
            print(f"Ошибка: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise  # Повторные попытки исчерпаны

def download_artifact(group_id, artifact_id, version):
    """Скачивает артефакт (JAR, POM, источники, документацию и метаданные)."""
    # Санитизируем версию (удаляем кавычки)
    sanitized_version = sanitize_path(version)
    base_path = f"{group_id.replace('.', '/')}/{artifact_id}/{sanitized_version}/"
    files = [
        f"{artifact_id}-{sanitized_version}.jar",
        f"{artifact_id}-{sanitized_version}.pom",
        f"{artifact_id}-{sanitized_version}-sources.jar",
        f"{artifact_id}-{sanitized_version}-javadoc.jar",
        f"{artifact_id}-{sanitized_version}.module",  # Модульные метаданные (если есть)
    ]
    
    # Скачиваем основные файлы
    for file in files:
        url = f"{BASE_URL}{base_path}{file}"
        # Очищаем имя файла от недопустимых символов
        sanitized_file = sanitize_filename(file)
        path = os.path.join(DOWNLOAD_DIR, "maven2", base_path.replace('/', os.sep), sanitized_file)
        
        # Проверяем, существует ли файл на сервере
        if file_exists(url):
            try:
                download_file(url, path)
            except requests.exceptions.RequestException:
                print(f"Не удалось скачать: {url}")
        else:
            print(f"Файл не найден: {url}")

    # Скачиваем maven-metadata.xml
    metadata_url = f"{BASE_URL}{group_id.replace('.', '/')}/{artifact_id}/maven-metadata.xml"
    metadata_path = os.path.join(DOWNLOAD_DIR, "maven2", group_id.replace('.', os.sep), artifact_id, "maven-metadata.xml")
    if file_exists(metadata_url):
        try:
            download_file(metadata_url, metadata_path)
        except requests.exceptions.RequestException:
            print(f"Не удалось скачать метаданные: {metadata_url}")
    else:
        print(f"Метаданные не найдены: {metadata_url}")

def main():
    # Загружаем зависимости из файла dependencies.json
    with open(DEPENDENCIES_FILE, "r", encoding="utf-8") as f:
        dependencies = json.load(f)

    # Проверяем количество артефактов
    total_artifacts = len(dependencies["artifacts"])
    print(f"Общее количество артефактов: {total_artifacts}")

    # Скачиваем артефакты, начиная с указанного индекса
    for index, artifact in enumerate(dependencies["artifacts"]):
        if index < START_ARTIFACT_INDEX:
            continue  # Пропускаем артефакты до указанного индекса
        group_id = artifact["group_id"]
        artifact_id = artifact["artifact_id"]
        latest_version = artifact["latest_version"]
        print(f"Скачивание артефакта {index + 1}/{total_artifacts}: {group_id}:{artifact_id}:{latest_version}")
        download_artifact(group_id, artifact_id, latest_version)

if __name__ == "__main__":
    main()