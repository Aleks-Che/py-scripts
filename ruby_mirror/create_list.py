import subprocess
import json

def get_dependencies():
    # Запускаем команду для получения списка зависимостей
    result = subprocess.run(['bundle', 'install', '--local'], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Ошибка при получении зависимостей:")
        print(result.stderr)
        return []
    
    # Парсим Gemfile.lock для получения списка зависимостей
    with open('Gemfile.lock', 'r') as file:
        lines = file.readlines()
    
    dependencies = []
    for line in lines:
        if line.strip().startswith(('  ', '*')) and ')' not in line:
            dep = line.strip().split(' ')
            dependencies.append(dep[0])
    
    # Сохраняем список зависимостей в файл
    with open('dependencies.json', 'w') as file:
        json.dump(dependencies, file)
    
    return dependencies

if __name__ == "__main__":
    dependencies = get_dependencies()
    print(f"Найдено {len(dependencies)} зависимостей.")