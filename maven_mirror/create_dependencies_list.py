import json
import requests
import time
import signal
import sys
from datetime import datetime
from tqdm import tqdm

DEPENDENCIES_FILE = "dependencies.json"
PROGRESS_FILE = "fetch_progress.json"
BATCH_SIZE = 20
MAVEN_SEARCH_URL = "https://search.maven.org/solrsearch/select"

class DependencyFetcher:
    def __init__(self):
        self.running = True
        self.progress = self.load_progress()
        signal.signal(signal.SIGINT, self.handle_interrupt)
        
    def load_progress(self):
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"current_start": 0, "total_found": None}
    
    def save_progress(self):
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(self.progress, f)
    
    def load_dependencies(self):
        try:
            with open(DEPENDENCIES_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"artifacts": [], "last_update": None}
    
    def save_dependencies(self, data):
        with open(DEPENDENCIES_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    def handle_interrupt(self, signum, frame):
        print("\nСохранение прогресса и завершение работы...")
        self.running = False
        self.save_progress()
        sys.exit(0)
    
    def fetch_artifacts(self):
        params = {
            "q": "*:*",
            "rows": BATCH_SIZE,
            "wt": "json"
        }
        
        # Получаем общее количество артефактов при первом запуске
        if self.progress["total_found"] is None:
            response = requests.get(MAVEN_SEARCH_URL, params={**params, "rows": 0})
            self.progress["total_found"] = response.json()["response"]["numFound"]
            self.save_progress()
        
        dependencies = self.load_dependencies()
        
        with tqdm(total=self.progress["total_found"], 
                 initial=self.progress["current_start"],
                 desc="Загрузка артефактов") as pbar:
            
            while self.running and self.progress["current_start"] < self.progress["total_found"]:
                params["start"] = self.progress["current_start"]
                
                try:
                    response = requests.get(MAVEN_SEARCH_URL, params=params)
                    data = response.json()
                    
                    for doc in data["response"]["docs"]:
                        artifact = {
                            "group_id": doc["g"],
                            "artifact_id": doc["a"],
                            "latest_version": doc["latestVersion"]
                        }
                        if artifact not in dependencies["artifacts"]:
                            dependencies["artifacts"].append(artifact)
                    
                    self.progress["current_start"] += BATCH_SIZE
                    pbar.update(BATCH_SIZE)
                    
                    # Сохраняем прогресс каждые 5000 артефактов
                    if self.progress["current_start"] % 5000 == 0:
                        self.save_progress()
                        dependencies["last_update"] = datetime.now().isoformat()
                        self.save_dependencies(dependencies)
                    
                    time.sleep(1)  # Задержка для избежания блокировки
                
                except Exception as e:
                    print(f"\nОшибка при получении артефактов: {str(e)}")
                    self.save_progress()
                    time.sleep(5)
                    continue
        
        if self.running:
            dependencies["last_update"] = datetime.now().isoformat()
            self.save_dependencies(dependencies)
            print("\nЗагрузка списка зависимостей завершена!")

if __name__ == "__main__":
    fetcher = DependencyFetcher()
    fetcher.fetch_artifacts()
