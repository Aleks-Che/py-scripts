from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import re
import random
import string

PLAYLIST_URL = 'https://www.youtube.com/playlist?list=PLZ7xEFnb-Itv6Sk-yBaZ5C_dJ8Pe6FK5T'

def safe_filename(s):
    return re.sub(r'[\\\/:\*\?"<>\|]', '_', s).strip()

def random_id(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)
driver.get(PLAYLIST_URL)
time.sleep(3)

# Скроллим страницу для загрузки всех видео
last_height = driver.execute_script("return document.documentElement.scrollHeight")
while True:
    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
    time.sleep(2)
    new_height = driver.execute_script("return document.documentElement.scrollHeight")
    if new_height == last_height:
        break
    last_height = new_height

# --- Получение Названия канала ---
channel_title = ''
try:
    # 1. Прямой блок с ссылкой на канал
    channel_elem = driver.find_element(By.XPATH, "//a[contains(@href, '/@')]")
    channel_title = channel_elem.text.strip()
except Exception:
    pass
if not channel_title:
    # 2. Поиск по всем ссылкам с '/@' в href
    links = driver.find_elements(By.TAG_NAME, 'a')
    for link in links:
        href = link.get_attribute('href')
        if href and '/@' in href:
            channel_title = link.text.strip()
            if channel_title:
                break
if not channel_title:
    # 3. Fallback: ищем по атрибуту aria-label (часто в новом дизайне)
    try:
        channel_elem = driver.find_element(By.XPATH, "//a[contains(@aria-label, '')]")
        channel_title = channel_elem.text.strip()
    except Exception:
        channel_title = ''
if not channel_title:
    # 4. В самом крайнем случае - из заголовка окна (в нем обычно есть название плейлиста и канала)
    title_words = driver.title.split(' - ')
    if len(title_words) > 1:
        channel_title = title_words[-1].replace('YouTube', '').strip()
if not channel_title:
    channel_title = random_id(6)

# --- Получение Названия плейлиста ---
try:
    playlist_elem = driver.find_element(By.CSS_SELECTOR, "h1.ytd-playlist-header-renderer")
    playlist_title = playlist_elem.text.strip()
except Exception:
    playlist_title = driver.title.split(' - ')[0].strip()
if not playlist_title:
    playlist_title = random_id(6)

# --- Сбор всех ссылок на видео ---
video_links = set()
videos = driver.find_elements(By.XPATH, '//a[@href and contains(@href, "/watch?v=")]')
for video in videos:
    href = video.get_attribute('href')
    if '&list=' in href:
        video_links.add(href)

driver.quit()

filename = f"{safe_filename(channel_title)}__{safe_filename(playlist_title)}.txt"
with open(filename, 'w', encoding='utf-8') as f:
    for link in sorted(video_links):
        f.write(link + '\n')

print(f'Ссылки сохранены в файл {filename}. Канал: {channel_title}, плейлист: {playlist_title}, видео: {len(video_links)}.')
