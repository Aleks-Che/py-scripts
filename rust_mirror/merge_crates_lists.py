import json
import glob

# Папка с файлами страниц
PAGES_DIR = "//"

# Файл для объединённого списка
OUTPUT_FILE = "combined_crates.json"

def combine_pages():
    combined_data = []
    
    # Читаем все файлы страниц
    for filepath in glob.glob(f"crates_page_*.json"):
        with open(filepath, 'r') as f:
            data = json.load(f)
            combined_data.extend(data)
    
    # Сохраняем объединённый список
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(combined_data, f, indent=2)

if __name__ == "__main__":
    combine_pages()