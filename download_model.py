import requests
from pathlib import Path
from tqdm import tqdm
import sys

MODELS = {
    "granite": {
        "url": "https://huggingface.co/unsloth/granite-4.0-h-350m-GGUF/resolve/main/granite-4.0-h-350m-Q5_K_M.gguf",
        "filename": "granite-4.0-h-350m-Q5_K_M.gguf"
    },
    "qwen": {
        "url": "https://huggingface.co/unsloth/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q5_K_M.gguf",
        "filename": "Qwen3-0.6B-Q5_K_M.gguf"
    }
}

MODEL_DIR = Path(__file__).parent / "models" / "local_llm"

def download_model(model_name: str):
    if model_name not in MODELS:
        print(f"Error: Model '{model_name}' not found. Available models: {', '.join(MODELS.keys())}")
        sys.exit(1)
    
    model_info = MODELS[model_name]
    MODEL_URL = model_info["url"]
    MODEL_PATH = MODEL_DIR / model_info["filename"]
    
    if MODEL_PATH.exists():
        print(f"Model already exists at {MODEL_PATH}")
        return
    
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading {model_name} model from HuggingFace...")
    print(f"URL: {MODEL_URL}")
    print(f"Destination: {MODEL_PATH}")
    
    response = requests.get(MODEL_URL, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    
    with open(MODEL_PATH, 'wb') as f, tqdm(
        desc="Downloading",
        total=total_size,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))
    
    print(f"\nModel downloaded successfully to {MODEL_PATH}")
    print(f"Model size: {MODEL_PATH.stat().st_size / (1024**3):.2f} GB")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python download_model.py <model_name>")
        print(f"Available models: {', '.join(MODELS.keys())}")
        sys.exit(1)
    
    model_name = sys.argv[1].lower()
    download_model(model_name)
