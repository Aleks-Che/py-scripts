from huggingface_hub import snapshot_download

model_names = [
    "lmstudio-community/Qwen3-32B-GGUF",
    "JetBrains/Mellum-4b-sft-python-gguf",
    "JetBrains/Mellum-4b-base-gguf",
    "jedisct1/MiMo-7B-RL-GGUF",
]

base_output_dir = "f://models"

for model_name in model_names:
    output_dir = f"{base_output_dir}/{model_name.split('/')[-1]}"
    
    print(f"Скачивание модели {model_name} в {output_dir}...")
    
    snapshot_download(
        repo_id=model_name,
        local_dir=output_dir,
        local_dir_use_symlinks=False,
        resume_download=True,          
        token=None                     
    )
    
    print(f"Модель {model_name} успешно скачана в {output_dir}\n")

print("Все модели успешно скачаны.")