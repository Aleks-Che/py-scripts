import os
import requests
import json
import time
from bs4 import BeautifulSoup

BASE_URL = "https://repo1.maven.org/maven2/"
DEPENDENCIES_FILE = "dependencies.json"
UPDATED_DEPENDENCIES_FILE = "updated_dependencies.json"
DOWNLOAD_DIR = "L:/maven_mirror"  # Используем одинарный прямой слеш
MAX_RETRIES = 3
RETRY_DELAY = 5
CHECK_NEW_VERSIONS = True  # Установите False, чтобы использовать версии из файла без проверки

# Индекс артефакта, с которого начинать скачивание (начиная с 0)
START_ARTIFACT_INDEX = 0

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

def get_latest_version(group_id, artifact_id):
    """Возвращает последнюю версию артефакта из Maven Central."""
    url = f"{BASE_URL}{group_id.replace('.', '/')}/{artifact_id}/"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            versions = [a.text.strip("/") for a in soup.find_all("a") if a.text.strip("/").replace(".", "").isdigit()]
            if versions:
                return sorted(versions, reverse=True)[0]  # Последняя версия
        return None
    except requests.exceptions.RequestException:
        return None

def download_file(url, path):
    """Скачивает файл по URL и сохраняет его в указанный путь с поддержкой продолжения."""
    # Сокращаем путь перед созданием директорий
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
                if r.status_code == 206:
                    print(f"Продолжение загрузки: {url} (с {downloaded_size} байт)")
                    mode = "ab"
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

def artifact_exists_locally(group_id, artifact_id, version):
    """Проверяет, существует ли артефакт локально."""
    sanitized_version = sanitize_path(version)
    base_path = f"{group_id.replace('.', '/')}/{artifact_id}/{sanitized_version}/"
    
    # Проверяем наличие основного JAR файла
    jar_path = os.path.join(DOWNLOAD_DIR, "maven2", base_path.replace('/', os.sep), 
                           f"{artifact_id}-{sanitized_version}.jar")
    
    # Проверяем наличие POM файла
    pom_path = os.path.join(DOWNLOAD_DIR, "maven2", base_path.replace('/', os.sep), 
                           f"{artifact_id}-{sanitized_version}.pom")
    
    # Если оба файла существуют, считаем, что артефакт уже скачан
    return os.path.exists(jar_path) and os.path.exists(pom_path)

def download_artifact(group_id, artifact_id, version):
    """Скачивает артефакт (JAR, POM, источники, документацию и метаданные)."""
    # Санитизируем версию (удаляем кавычки)
    sanitized_version = sanitize_path(version)
    
    # Проверяем, существует ли артефакт локально
    if artifact_exists_locally(group_id, artifact_id, version):
        print(f"Артефакт {group_id}:{artifact_id}:{version} уже существует локально. Пропускаем скачивание.")
        return
    
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
    
    # Список для хранения обновленных артефактов и изменившихся версий
    updated_artifacts = []
    changed_versions = []

    # Скачиваем артефакты, начиная с указанного индекса
    for index, artifact in enumerate(dependencies["artifacts"]):
        if index < START_ARTIFACT_INDEX:
            continue  # Пропускаем артефакты до указанного индекса
            
        group_id = artifact["group_id"]
        artifact_id = artifact["artifact_id"]
        current_version = artifact["latest_version"]
        
        # Проверяем новую версию, если флаг CHECK_NEW_VERSIONS установлен
        version_to_download = current_version
        if CHECK_NEW_VERSIONS:
            print(f"Проверка новой версии для {group_id}:{artifact_id}")
            latest_version = get_latest_version(group_id, artifact_id)
            if latest_version and latest_version != current_version:
                print(f"Найдена новая версия: {latest_version} (текущая: {current_version})")
                version_to_download = latest_version
                changed_versions.append({
                    "group_id": group_id,
                    "artifact_id": artifact_id,
                    "old_version": current_version,
                    "new_version": latest_version
                })
            elif not latest_version:
                print(f"Не удалось получить новую версию для {group_id}:{artifact_id}, используем текущую: {current_version}")
            else:
                print(f"Версия актуальна: {current_version}")
        
        # Добавляем артефакт с актуальной версией в список обновленных
        updated_artifacts.append({
            "group_id": group_id,
            "artifact_id": artifact_id,
            "latest_version": version_to_download
        })
        
        # Скачиваем артефакт
        print(f"Скачивание артефакта {index + 1}/{total_artifacts}: {group_id}:{artifact_id}:{version_to_download}")
        download_artifact(group_id, artifact_id, version_to_download)
    
    # Сохраняем обновленные зависимости
    with open(UPDATED_DEPENDENCIES_FILE, "w", encoding="utf-8") as f:
        json.dump({"artifacts": updated_artifacts}, f, indent=2)
    print(f"Обновлённые зависимости сохранены в {UPDATED_DEPENDENCIES_FILE}")
    
    # Сохраняем список изменённых версий, если есть изменения
    if changed_versions:
        with open("changed_versions.json", "w", encoding="utf-8") as f:
            json.dump({"changed_artifacts": changed_versions}, f, indent=2)
        print(f"Список изменённых версий сохранён в changed_versions.json")

if __name__ == "__main__":
    main()
