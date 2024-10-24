import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from tqdm import tqdm
import re
from requests.exceptions import ConnectionError, RequestException

# Скрипт для парсинга страниц сайта gov.zakupki.ru по ссылкам из csv-файла

DELAY_MIN = 3  # минимальная задержка в секундах
DELAY_MAX = 7  # максимальная задержка в секундах
APPEND_TO_FILE = True  # True для дописывания, False для перезаписи
START_LINK_INDEX = 10  # Индекс ссылки, с которой начать парсинг (0-based)
CONTINUE_FROM_LAST = True  # Продолжить с места остановки
MAX_RETRIES = 6  # Максимальное количество повторных запросов
RETRY_DELAY = 10  # задержка при повторном подключении

PARSING_RULES = [
    [['1', 'span', 'text-break d-block']],
    [['1', 'div', 'sectionMainInfo borderRight col-3 colSpaceBetween'], ['1', 'div', 'price'], ['1', 'span', 'cardMainInfo__content cost']],
    ['inn_extract', 'ИНН:'],
    ['table_extract', 'Адрес места нахождения', 'blockInfo__table tableBlock grayBorderBottom'],
    ['table_extract', 'Телефон, электронная почта', 'blockInfo__table tableBlock grayBorderBottom'],
    # Добавьте больше правил по необходимости
]

CSV_HEADERS = [
    'Ссылка',
    'Объекты закупки',
    'Цена контракта',
    'ИНН',
    'Адрес',
    'Контакты'
    # Добавьте другие названия столбцов по необходимости
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
]

def get_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Referer': 'https://zakupki.gov.ru/',
        'Origin': 'https://zakupki.gov.ru',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Ch-Ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Priority': 'u=1, i',
    }

def extract_inn(soup, label):
    section = soup.find('section', class_='section blockInfo__section')
    if section:
        inn_span = section.find('span', string=label)
        if inn_span:
            next_span = inn_span.find_next('span')
            if next_span:
                return next_span.text.strip()
    return None

def parse_element(soup, rule):
    if isinstance(rule[0], str):
        if rule[0] == 'table_extract':
            return extract_table_data(soup, rule[1], rule[2])
        elif rule[0] == 'inn_extract':
            return extract_inn(soup, rule[1])
    element = soup
    for index, tag, class_name in rule:
        if class_name:
            elements = element.find_all(tag, class_=class_name)
        else:
            elements = element.find_all(tag)
        
        if not elements or int(index) > len(elements):
            return None
        
        element = elements[int(index) - 1]
    
    # Очистка текста от лишних пробелов и переносов строк
    text = element.text.strip()
    cleaned_text = re.sub(r'\s+', ' ', text)
    return cleaned_text

def extract_table_data(soup, header_text, table_class):
    table = soup.find('table', class_=table_class)
    if not table:
        return None
    
    headers = table.find_all('th')
    for i, header in enumerate(headers):
        if header_text in header.text:
            body = table.find('tbody')
            if body:
                rows = body.find_all('tr')
                column_data = []
                for row in rows:
                    cells = row.find_all('td')
                    if i < len(cells):
                        column_data.append(cells[i].text.strip())
                raw_data = ' | '.join(column_data)
                # Заменяем множественные пробелы и переносы строк на один пробел
                cleaned_data = re.sub(r'\s+', ' ', raw_data)
                return cleaned_data.strip()
    return None

last_processed_link = ''
if CONTINUE_FROM_LAST:
    try:
        with open('parsed_data.csv', 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            last_row = list(reader)[-1]
            last_processed_link = last_row[0]
    except (FileNotFoundError, IndexError):
        pass

# Чтение ссылок из CSV
with open('links.csv', 'r') as csvfile:
    reader = csv.reader(csvfile)
    next(reader)  # Пропускаем заголовок
    links = [row[0] for row in reader]

if CONTINUE_FROM_LAST:
    try:
        start_index = links.index(last_processed_link) + 1
    except ValueError:
        start_index = 0
else:
    start_index = START_LINK_INDEX

links = links[start_index:]

# Определяем режим открытия файла
file_mode = 'a' if APPEND_TO_FILE else 'w'

# Парсинг страниц и сохранение данных
with open('parsed_data.csv', file_mode, encoding='utf-8-sig', newline='') as csvfile:
    writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
   
    # Записываем заголовки только если файл новый
    if not APPEND_TO_FILE:
        writer.writerow(CSV_HEADERS)

    session = requests.Session()

    for link in tqdm(links, desc="Прогресс парсинга", unit="ссылка"):
        retries = 0
        while retries < MAX_RETRIES:
            try:
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
                response = session.get(link, headers=get_headers(), timeout=10)
                response.raise_for_status() # Проверяем статус ответа
               
                soup = BeautifulSoup(response.content, 'html.parser')

                row_data = [link]
                for rule in PARSING_RULES:
                    parsed_data = parse_element(soup, rule)
                    row_data.append(parsed_data if parsed_data else '')
                   
                writer.writerow(row_data)
                break
           
            except (ConnectionError, RequestException) as e:
                retries += 1
                print(f"Произошла ошибка: {e}")
                if retries < MAX_RETRIES:
                    print(f"Повторная попытка через {RETRY_DELAY} секунд... (Попытка {retries + 1} из {MAX_RETRIES})")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"Достигнуто максимальное количество попыток для ссылки: {link}")
       
        if retries == MAX_RETRIES:
            print(f"Пропуск ссылки из-за постоянных ошибок: {link}")

print(f"Парсинг завершен. Данные {'добавлены в' if APPEND_TO_FILE else 'сохранены в'} parsed_data.csv")

