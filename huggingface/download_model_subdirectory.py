from huggingface_hub import snapshot_download
import os

NUM_THREADS = 3  # Количество потоков <button class="citation-flag" data-index="2">
# SUBDIRECTORIES = [
#     "Tess-3-Llama-3.1-405B-IQ2_M",
#     "Tess-3-Llama-3.1-405B-IQ3_XXS",
#     "Tess-3-Llama-3.1-405B-Q3_K_M",
#     "Tess-3-Llama-3.1-405B-Q4_K_M",
#     "Tess-3-Llama-3.1-405B-Q5_K_M",
#     "Tess-3-Llama-3.1-405B-Q6_K",  
#     "Tess-3-Llama-3.1-405B-Q8_0",  
# ]
# REPO_ID = "bartowski/Tess-3-Llama-3.1-405B-GGUF"
# OUTPUT_DIR = "K://tess-3-Llama-3.1-405B-GGUF"

SUBDIRECTORIES = [
    # "perplexity-ai_r1-1776-IQ1_M",
    # "perplexity-ai_r1-1776-IQ2_XXS",
    # "perplexity-ai_r1-1776-Q3_K_M",
    # "perplexity-ai_r1-1776-Q4_K_M",
    # "perplexity-ai_r1-1776-Q5_K_M",
    # "perplexity-ai_r1-1776-Q6_K",
    "Q8_0",
    "Q3_K_M",
    # "Q4_K_M",
    # "Q5_K_M",
    # "Q6_K",
    "BF16",
    # "Tess-3-Llama-3.1-405B-Q4_K_M",
    # "Tess-3-Llama-3.1-405B-Q5_K_M",  
    # "Tess-3-Llama-3.1-405B-Q6_K",  
    # "Tess-3-Llama-3.1-405B-Q8_0",
]
REPO_ID = "unsloth/Qwen3-235B-A22B-GGUF"
OUTPUT_DIR = "F://models//unsloth-Qwen3-235B-A22B-GGUF"

# Создание базовой директории
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Генерация шаблонов для фильтрации файлов
allow_patterns = [f"{subdir}/*" for subdir in SUBDIRECTORIES]

# Скачивание с многопоточностью
snapshot_download(
    repo_id=REPO_ID,
    allow_patterns=allow_patterns, 
    local_dir=OUTPUT_DIR,
    repo_type="model",
    local_dir_use_symlinks=False,
    max_workers=NUM_THREADS,
)

print(f"Файлы из подкаталогов {SUBDIRECTORIES} успешно скачаны в {OUTPUT_DIR}")