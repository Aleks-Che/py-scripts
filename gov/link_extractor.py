import requests
from bs4 import BeautifulSoup
import csv
import random
import time
import re

SITE_URL = "https://zakupki.gov.ru/epz/contract/search/results.html?searchString=&morphology=on&search-filter=%D0%94%D0%B0%D1%82%D0%B5+%D0%BE%D0%B1%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F&savedSearchSettingsIdHidden=&fz44=on&fz94=on&contractStageList_0=on&contractStageList=0&contractInputNameDefenseOrderNumber=&contractInputNameContractNumber=&contractPriceFrom=1000000000&rightPriceRurFrom=&priceFromUnitGWS=&contractPriceTo=&rightPriceRurTo=&priceToUnitGWS=&currencyCode=ANY&nonBudgetCodesList=&budgetLevelsIdHidden=&budgetLevelsIdNameHidden=%7B%7D&budgetName=&customerPlace=&customerPlaceCodes=&contractDateFrom=&contractDateTo=&publishDateFrom=&publishDateTo=&updateDateFrom=&updateDateTo=&placingWayList=&selectedLaws=&sortBy=UPDATE_DATE&pageNumber=2&sortDirection=false&recordsPerPage=_50&showLotsInfoHidden=true"
LINK_CONTAINER_CLASS = "registry-entry__header-mid__number"
BASE_URL = "https://zakupki.gov.ru"
APPEND_TO_FILE = True  # True для дозаписывания, False для перезаписи
EXTRACT_MULTIPLE_PAGES = True # True для извлечения ссылок со всех страниц, False для извлечения ссылок только с START_PAGE страницы
START_PAGE = 10 # Начальная страница для извлечения ссылок
END_PAGE = 20  # Конечная страница для извлечения ссылок
DELAY_MIN = 3  # минимальная задержка в секундах
DELAY_MAX = 7  # максимальная задержка в секундах
SITE_URL = re.sub(r'pageNumber=\d+', 'pageNumber={page_number}', SITE_URL)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.google.com/',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

existing_links = set()
if APPEND_TO_FILE:
    with open('links.csv', 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Пропускаем заголовок
        existing_links = set(row[0] for row in reader)

def extract_links_from_page(page_number):
    current_url = SITE_URL.format(page_number=page_number)
    response = session.get(current_url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.content, 'html.parser')
    links = soup.find_all('div', class_=LINK_CONTAINER_CLASS)
    return [BASE_URL + link.find('a')['href'] for link in links if link.find('a')]

# Получаем веб-страницу
session = requests.Session()
response = session.get(SITE_URL, headers=headers, timeout=10)
time.sleep(random.uniform(1, 3))
soup = BeautifulSoup(response.content, 'html.parser')

# Извлекаем ссылки
links = soup.find_all('div', class_=LINK_CONTAINER_CLASS)
extracted_links = [BASE_URL + link.find('a')['href'] for link in links if link.find('a')]

# Сохраняем ссылки в CSV
file_mode = 'a' if APPEND_TO_FILE else 'w'
with open('links.csv', file_mode, newline='') as csvfile:
    writer = csv.writer(csvfile)
    if not APPEND_TO_FILE or csvfile.tell() == 0:
        writer.writerow(['Ссылка'])

    if EXTRACT_MULTIPLE_PAGES:
        for page in range(START_PAGE, END_PAGE + 1):
            extracted_links = extract_links_from_page(page)
            for link in extracted_links:
                if link not in existing_links:
                    writer.writerow([link])
                    existing_links.add(link)
                else:
                    print(f"Ссылка уже существует: {link}")
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    else:
        extracted_links = extract_links_from_page(START_PAGE)
        for link in extracted_links:
            if link not in existing_links:
                writer.writerow([link])
                existing_links.add(link)
            else:
                print(f"Ссылка уже существует: {link}")

print(f"Извлечение завершено. Ссылки {'добавлены в' if APPEND_TO_FILE else 'сохранены в'} links.csv")

