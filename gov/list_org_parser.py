import requests
from bs4 import BeautifulSoup
import time
import random
from tqdm import tqdm
import logging
import pandas as pd
import os
import signal
import sys

# Скрипт для парсинга страниц сайта list-org.com по ИНН из файла INPUT_FILE

BASE_URL = 'https://www.list-org.com/search?val='
DELAY_MIN = 4  # минимальный порог для случайной задержки в секундах между переходами по ссылкам
DELAY_MAX = 9  # максимальный порог для случайной задержки в секундах между переходами по ссылкам
START_INDEX = 0  # С какой позиции брать значения (0 это первое значение находящееся во второ строке, первая строке это заголовок)
MAX_RETRIES = 5  # Максимальное количество повторных запросов
RETRY_DELAY = 4  # Задержка между повторными запросами в секундах
APPEND_TO_FILE = False  # Set to True to append, False to overwrite
INPUT_FILE = 'parsed_data.xlsx' # Входной файл, из столбца ИНН берется значения для подстановки в ссылку
OUTPUT_FILE = 'parsed_data_updated.xlsx'  # Имя выходного файла, в который будут складываться результаты парсинга
USE_PROXY = False  # Установите False, чтобы отключить использование прокси

PROXY_SERVERS = [
    {"ip": "212.69.125.33", "port": "80", "protocol": "HTTP"},
    {"ip": "188.32.100.60", "port": "8080", "protocol": "HTTP"},
    {"ip": "81.200.149.178", "port": "80", "protocol": "HTTP"},
    {"ip": "77.232.128.191", "port": "80", "protocol": "HTTP"},
    {"ip": "94.243.131.141", "port": "1080", "protocol": "SOCKS5"},
    {"ip": "85.21.233.231", "port": "1337", "protocol": "SOCKS5"},
    {"ip": "212.33.228.127", "port": "1080", "protocol": "SOCKS5"},
    {"ip": "37.193.46.11", "port": "1080", "protocol": "SOCKS5"},
    {"ip": "94.230.127.180", "port": "1080", "protocol": "SOCKS5"},
    {"ip": "188.124.230.43", "port": "17662", "protocol": "SOCKS5"},
    {"ip": "193.124.181.187", "port": "1080", "protocol": "SOCKS5"}
]

current_proxy_index = 0

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# функция для сохранения результата
def save_intermediate_results(data, output_file):
    df = pd.DataFrame(data)
    if os.path.exists(output_file):
        with pd.ExcelWriter(output_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
    else:
        df.to_excel(output_file, index=False)

# обработчик сигнала прерывания скрипта
def signal_handler(sig, frame):
    print("\nПрерывание обнаружено. Сохранение текущих результатов...")
    save_intermediate_results(rows, OUTPUT_FILE)
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Origin': 'https://www.list-org.com',
        'Referer': 'https://www.list-org.com/',
        'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'Priority': 'u=1, i',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

# Получение следующего прокси
def get_next_proxy():
    global current_proxy_index
    if current_proxy_index >= len(PROXY_SERVERS):
        current_proxy_index = 0
    proxy = PROXY_SERVERS[current_proxy_index]
    current_proxy_index += 1
    return f"{proxy['protocol'].lower()}://{proxy['ip']}:{proxy['port']}"

def extract_data(soup):
    data = {}
    
    # Найдем таблицу
    table = soup.find('table', class_='table table-sm')
    
    if table:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) == 2:
                label = cells[0].text.strip()
                value = cells[1].text.strip()
                
                if 'Полное юридическое наименование:' in label:
                    data['юридическое наименование'] = value
                    if not value:
                        logging.info("Отсутствует юридическое наименование")
                
                elif 'Численность персонала:' in label:
                    data['Численность персонала'] = value
                    if not value:
                        logging.info("Отсутствует численность персонала")
    
    # Извлечение телефонного номера
    phone_a = soup.find('a', class_='clipboards nwra')
    if phone_a:
        phone_span = phone_a.find('span')
        if phone_span:
            data['Телефон list-org'] = phone_span.text.strip()
    else:
        logging.info("Отсутствует телефон")
    
    # Извлечение email
    email_a = soup.find('a', class_='wwbw')
    if email_a:
        data['E-mail list-org'] = email_a.text.strip()
    else:
        logging.info("Отсутствует email")
    
    # Извлечение ОКВЭД
    okved_div = soup.find('div', class_='card w-100 p-1 p-lg-3 mt-2')
    if not okved_div:
        logging.info("Отсутствует ОКВЭД")
    
    # Извлечение выручки
    revenue_row = soup.find('td', string='Выручка')
    if revenue_row:
        data['Выручка'] = revenue_row.find_next('td').text.strip()
        if not data['Выручка']:
            logging.info("Отсутствует выручка")
    else:
        logging.info("Отсутствует выручка")
    
    return data

# Парсинг списка организаций
def parse_list_org(inn):
    session = requests.Session()
    
    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            if USE_PROXY:
                proxy = get_next_proxy()
                proxies = {"http": proxy, "https": proxy}
            else:
                proxies = None
            
            url = BASE_URL + inn
            response = session.get(url, headers=get_headers(), proxies=proxies, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Проверка на наличие капчи
            captcha_block = soup.find('div', class_='g-recaptcha')
            if captcha_block:
                print(f"\n{'='*50}")
                print("ВНИМАНИЕ! ОБНАРУЖЕНА CAPTCHA!")
                print(f"Текущий ИНН: {inn}")
                print(f"Требуется ручной ввод капчи: {url}")
                print("После прохождения капчи нажмите Enter для продолжения...")
                print(f"{'='*50}\n")
                input()
                continue  # Повторяет текущую попытку без увеличения attempt
            
            # Переход на страницу организации
            org_list = soup.find('div', class_='org_list')
            if org_list:
                company_link = org_list.find('p').find('label').find('a')
                if company_link:
                    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
                    company_url = 'https://www.list-org.com' + company_link['href']
                    response = session.get(company_url, headers=get_headers(), proxies=proxies, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                    return extract_data(soup)
            return None

        # Обработка исключений    
        except (requests.RequestException, ConnectionError) as e:
            logging.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            attempt += 1  # Увеличиваем счетчик только при ошибках запроса
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                logging.error(f"Failed to parse data for INN {inn} after {MAX_RETRIES} attempts")
                return None

df = pd.read_excel(INPUT_FILE)

rows = df.to_dict('records')

#   Основной цикл парсинга страниц list-org с подстановкой ИНН искомой организации в поиск
for index, row in tqdm(enumerate(rows[START_INDEX:], start=START_INDEX), desc="Прогресс парсинга", unit="ссылка", total=len(rows)-START_INDEX):
    inn = str(row['ИНН'])
    if inn:
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        data = parse_list_org(inn)
        if data:
            row.update(data)
        save_intermediate_results(rows, OUTPUT_FILE)

# Сохранение обновленных данных
if os.path.exists(OUTPUT_FILE) and APPEND_TO_FILE:
    existing_df = pd.read_excel(OUTPUT_FILE)
    df_updated = pd.DataFrame(rows)
    
    # Добавляем новые столбцы, если они есть
    for column in df_updated.columns:
        if column not in existing_df.columns:
            existing_df[column] = df_updated[column]
    
    # Обновляем существующие строки и добавляем новые
    existing_df.update(df_updated)
    new_rows = df_updated[~df_updated.index.isin(existing_df.index)]
    final_df = pd.concat([existing_df, new_rows])
else:
    final_df = pd.DataFrame(rows)

# Сохранение обновленного файла
with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
    final_df.to_excel(writer, index=False)

print(f"Парсинг завершен. {'Обновленные' if APPEND_TO_FILE else 'Новые'} данные {'добавлены в' if APPEND_TO_FILE else 'сохранены в'} {OUTPUT_FILE}")

