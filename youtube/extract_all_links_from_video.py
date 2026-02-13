from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

URL = "https://www.youtube.com/@arminvanbuuren/videos"
OUTPUT_FILE = "video_links.txt"
SCROLL_PAUSE = 1.3
MAX_SCROLLS = 30

driver = webdriver.Chrome()
driver.maximize_window()
driver.get(URL)
time.sleep(5)

# Активируем ожидания
wait = WebDriverWait(driver, 20) # до 20 секунд

# Скроллируем вниз для подгрузки видео
last_h = 0
for _ in range(MAX_SCROLLS):
    driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
    time.sleep(SCROLL_PAUSE)
    new_h = driver.execute_script("return document.documentElement.scrollHeight")
    if new_h == last_h:
        break
    last_h = new_h

# Ждем, пока появятся хотя бы некоторые видеоэлементы
wait.until(EC.presence_of_element_located(
    (By.CSS_SELECTOR, "ytd-rich-item-renderer")
))

items = driver.find_elements(By.CSS_SELECTOR, 'ytd-rich-item-renderer a#thumbnail')
video_links = set()
for itm in items:
    href = itm.get_attribute("href")
    if href and "/watch?v=" in href:
        video_links.add(href)

print(f"[+] Найдено видео: {len(video_links)}")
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for v in sorted(video_links):
        f.write(f"{v}\n")

print(f"[+] Все ссылки сохранены в {OUTPUT_FILE}")
driver.quit()
