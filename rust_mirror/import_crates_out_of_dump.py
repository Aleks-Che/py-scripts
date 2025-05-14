import psycopg2
import json
from datetime import datetime

# Параметры подключения к PostgreSQL
DB_CONFIG = {
    "dbname": "rust",
    "user": "Aleks",
    "password": "xxx",
    "host": "localhost",
    "port": 5432
}
PAGE_SIZE = 50000

def datetime_serializer(obj):
    """Сериализует объекты datetime в строки."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def fetch_data(start_id=None):
    """Выполняет запрос к базе данных с пагинацией."""
    query = """
        SELECT id, name, updated_at, created_at, description, homepage, repository, readme, documentation
        FROM crates
        WHERE id > %s
        ORDER BY id
        LIMIT %s;
    """
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (start_id or 0, PAGE_SIZE))
            columns = [desc[0] for desc in cur.description]  # Получаем имена столбцов
            data = cur.fetchall()
            return columns, data

def save_to_file(data, columns, filename):
    """Сохраняет данные в файл."""
    with open(filename, 'w') as f:
        # Преобразуем данные в список словарей
        data_dicts = [dict(zip(columns, row)) for row in data]
        
        # Сериализуем данные с учётом datetime
        json.dump(data_dicts, f, indent=2, default=datetime_serializer)

def main():
    start_id = None
    page = 1

    while True:
        print(f"Fetching page {page}...")
        columns, data = fetch_data(start_id)
        if not data:
            break

        # Сохраняем данные в файл
        save_to_file(data, columns, f"crates_page_{page}.json")

        # Обновляем start_id для следующей страницы
        start_id = data[-1][0]  # Предполагаем, что id — это первый столбец
        page += 1

    print("Data fetching completed.")

if __name__ == "__main__":
    main()