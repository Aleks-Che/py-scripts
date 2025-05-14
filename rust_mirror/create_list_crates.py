import requests
import json
import time

# Константа с именем файла для сохранения списка crates
CRATES_LIST_FILE = "crates_list.json"

# URL для получения списка всех crates
CRATES_LIST_URL = "https://crates.io/api/v1/crates?per_page=100&page={page}"

def get_all_crates():
    crates = []
    page = 1
    while True:
        print(f"Fetching page {page}...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(CRATES_LIST_URL.format(page=page), headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch page {page}. Status code: {response.status_code}")
            break
        data = response.json()
        crates.extend(data['crates'])
        if not data['meta']['next_page']:
            break
        page += 1
        time.sleep(1)  # Задержка в 1 секунду между запросами
    return crates

def save_crates_list(crates):
    with open(CRATES_LIST_FILE, 'w') as f:
        json.dump(crates, f, indent=2)
    print(f"Saved {len(crates)} crates to {CRATES_LIST_FILE}")

def main():
    crates = get_all_crates()
    save_crates_list(crates)

if __name__ == "__main__":
    main()