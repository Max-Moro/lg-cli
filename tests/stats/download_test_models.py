#!/usr/bin/env python3
"""
Скрипт для скачивания тестовых моделей токенизации.

Скачивает модели из HuggingFace Hub и помещает их в tests/stats/resources/
для использования в тестах без повторного скачивания.

Usage:
    python tests/stats/download_test_models.py
"""

import json
import shutil
from pathlib import Path

# Определяем пути
SCRIPT_DIR = Path(__file__).parent
RESOURCES_DIR = SCRIPT_DIR / "resources"
MANIFEST_FILE = RESOURCES_DIR / "models_manifest.json"


def download_hf_tokenizer(repo_id: str, target_dir: Path) -> None:
    """
    Скачивает HuggingFace tokenizer.
    
    Args:
        repo_id: ID репозитория на HF (например, "gpt2")
        target_dir: Целевая директория для сохранения
    """
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("ERROR: huggingface-hub not installed")
        print("Install: pip install huggingface-hub")
        return
    
    print(f"Downloading tokenizer: {repo_id}")
    
    try:
        # Скачиваем tokenizer.json
        tokenizer_file = hf_hub_download(
            repo_id=repo_id,
            filename="tokenizer.json"
        )
        
        # Копируем в нашу директорию
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tokenizer_file, target_dir / "tokenizer.json")
        
        print(f"✓ Downloaded to {target_dir}")
    except Exception as e:
        print(f"✗ Failed to download {repo_id}: {e}")


def download_sentencepiece_model(repo_id: str, target_dir: Path) -> None:
    """
    Скачивает SentencePiece модель.
    
    Args:
        repo_id: ID репозитория на HF (например, "google/gemma-2-2b")
        target_dir: Целевая директория для сохранения
    """
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("ERROR: huggingface-hub not installed")
        print("Install: pip install huggingface-hub")
        return
    
    print(f"Downloading SentencePiece model: {repo_id}")
    
    try:
        # Пробуем разные стандартные имена файлов
        model_file = None
        for filename in ["tokenizer.model", "spiece.model", "sentencepiece.model"]:
            try:
                model_file = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename
                )
                break
            except Exception:
                continue
        
        if model_file is None:
            raise FileNotFoundError(f"No SentencePiece model found in {repo_id}")
        
        # Копируем в нашу директорию
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем как tokenizer.model (стандартное имя)
        shutil.copy2(model_file, target_dir / "tokenizer.model")
        
        print(f"✓ Downloaded to {target_dir}")
    except Exception as e:
        print(f"✗ Failed to download {repo_id}: {e}")


def main():
    """Основная функция скачивания."""
    print("=" * 60)
    print("Downloading test tokenizer models")
    print("=" * 60)
    print()
    
    # Загружаем манифест
    if not MANIFEST_FILE.exists():
        print(f"ERROR: Manifest not found: {MANIFEST_FILE}")
        return 1
    
    with MANIFEST_FILE.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    # Скачиваем HuggingFace tokenizers
    print("HuggingFace Tokenizers:")
    print("-" * 40)
    for repo_id, info in manifest.get("tokenizers", {}).items():
        target_dir = RESOURCES_DIR / "tokenizers" / repo_id.replace("/", "--")
        
        if (target_dir / "tokenizer.json").exists():
            print(f"⊙ Already downloaded: {repo_id}")
            continue
        
        download_hf_tokenizer(repo_id, target_dir)
    
    print()
    
    # Скачиваем SentencePiece модели
    print("SentencePiece Models:")
    print("-" * 40)
    for repo_id, info in manifest.get("sentencepiece", {}).items():
        target_dir = RESOURCES_DIR / "sentencepiece" / repo_id.replace("/", "--")
        
        if (target_dir / "tokenizer.model").exists():
            print(f"⊙ Already downloaded: {repo_id}")
            continue
        
        download_sentencepiece_model(repo_id, target_dir)
    
    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
