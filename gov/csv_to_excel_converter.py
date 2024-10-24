import pandas as pd
import re

# Конвертер CSV в Excel
INPUT_CSV_FILE = 'parsed_data_updated.csv'
OUTPUT_EXCEL_FILE = 'parsed_data_updated.xlsx'

def clean_text(text):
    if isinstance(text, str):
        return re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    return text

def csv_to_excel(csv_file, excel_file):
    df = pd.read_csv(csv_file)
    df = df.map(clean_text)
    df.to_excel(excel_file, index=False, engine='openpyxl')
    print(f"Конвертация завершена. Excel файл сохранен как {excel_file}")

if __name__ == "__main__":
    csv_to_excel(INPUT_CSV_FILE, OUTPUT_EXCEL_FILE)
