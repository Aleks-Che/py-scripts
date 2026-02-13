from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time, re, random, string, os

# -------------------- USER SETTINGS --------------------
CHANNEL_PLAYLISTS_URL = "https://www.youtube.com/@electronicsclub1/playlists"   # ← change here
OUTPUT_DIR            = "electronicsclub1"                                 # folder for txt-files
SCROLL_PAUSE          = 1.5                                              # seconds between scrolls
PLAYLIST_PAUSE        = 15                                               # seconds between playlists
# -------------------------------------------------------

os.makedirs(OUTPUT_DIR, exist_ok=True)

def safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '_', s).strip()

def rnd_id(k: int = 6) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=k))

# ---------- 1. scrape playlist links ----------
driver = webdriver.Chrome()
driver.maximize_window()
driver.get(CHANNEL_PLAYLISTS_URL)
time.sleep(8)                       # cookies / initial load

# scroll until nothing new appears
for _ in range(25):
    driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
    time.sleep(SCROLL_PAUSE)

playlist_links = []
for a in driver.find_elements(
        By.XPATH,
        "//a[contains(@href,'/playlist?list=') and (contains(text(),'Посмотреть весь плейлист') or contains(text(),'Весь курс'))]"
):
    href = a.get_attribute("href")
    if href and "list=" in href:
        playlist_links.append(href)

print(f"[+] Found {len(playlist_links)} playlists")

# ---------- 2. process every playlist ----------
for idx, pl_url in enumerate(playlist_links, 1):
    print(f"[{idx:>3}/{len(playlist_links)}]  {pl_url}")

    driver.get(pl_url)
    time.sleep(3)

    # scroll to load all videos
    last_h = driver.execute_script("return document.documentElement.scrollHeight")
    while True:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(2)
        new_h = driver.execute_script("return document.documentElement.scrollHeight")
        if new_h == last_h:
            break
        last_h = new_h

    # playlist title
    try:
        title = driver.find_element(By.CSS_SELECTOR, "h1.ytd-playlist-header-renderer").text.strip()
    except Exception:
        title = driver.title.split(" - ")[0].strip()
    if not title:
        title = rnd_id()

    # collect unique video links
    videos = set()
    for a in driver.find_elements(By.XPATH, '//a[@href and contains(@href,"/watch?v=")]'):
        href = a.get_attribute("href")
        if href and "&list=" in href:
            videos.add(href)

    # save
    file_name = safe_name(title) + ".txt"
    with open(os.path.join(OUTPUT_DIR, file_name), "w", encoding="utf-8") as f:
        f.writelines(f"{v}\n" for v in sorted(videos))

    print(f"      └─ {len(videos)} videos → {file_name}")

    if idx < len(playlist_links):
        time.sleep(PLAYLIST_PAUSE)

driver.quit()
print("\nAll done!")