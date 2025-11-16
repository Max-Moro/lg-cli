#!/usr/bin/env python3
"""
Script to download test models for tokenization.

Downloads models from HuggingFace Hub and puts them in tests/stats/resources/
for use in tests without re-downloading.

Usage:
    python tests/stats/download_test_models.py
"""

import json
import shutil
from pathlib import Path

# Define paths
SCRIPT_DIR = Path(__file__).parent
RESOURCES_DIR = SCRIPT_DIR / "resources"
MANIFEST_FILE = RESOURCES_DIR / "models_manifest.json"


def download_hf_tokenizer(repo_id: str, target_dir: Path) -> None:
    """
    Downloads HuggingFace tokenizer.

    Args:
        repo_id: HF repository ID (e.g., "gpt2")
        target_dir: Target directory for saving
    """
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("ERROR: huggingface-hub not installed")
        print("Install: pip install huggingface-hub")
        return

    print(f"Downloading tokenizer: {repo_id}")

    try:
        # Download tokenizer.json
        tokenizer_file = hf_hub_download(
            repo_id=repo_id,
            filename="tokenizer.json"
        )

        # Copy to our directory
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tokenizer_file, target_dir / "tokenizer.json")

        print(f"✓ Downloaded to {target_dir}")
    except Exception as e:
        print(f"✗ Failed to download {repo_id}: {e}")


def download_sentencepiece_model(repo_id: str, target_dir: Path) -> None:
    """
    Downloads SentencePiece model.

    Args:
        repo_id: HF repository ID (e.g., "google/gemma-2-2b")
        target_dir: Target directory for saving
    """
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("ERROR: huggingface-hub not installed")
        print("Install: pip install huggingface-hub")
        return

    print(f"Downloading SentencePiece model: {repo_id}")

    try:
        # Try different standard file names
        model_file = None
        last_error = None
        for filename in ["tokenizer.model", "spiece.model", "sentencepiece.model"]:
            try:
                model_file = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename
                )
                print(f"  Found: {filename}")
                break
            except Exception as e:
                last_error = e
                continue

        if model_file is None:
            error_msg = f"No SentencePiece model found in {repo_id}"
            if last_error:
                error_msg += f" (last error: {last_error})"
            raise FileNotFoundError(error_msg)

        # Copy to our directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Save as tokenizer.model (standard name)
        shutil.copy2(model_file, target_dir / "tokenizer.model")

        print(f"✓ Downloaded to {target_dir}")
    except Exception as e:
        print(f"✗ Failed to download {repo_id}: {e}")


def main():
    """Main download function."""
    print("=" * 60)
    print("Downloading test tokenizer models")
    print("=" * 60)
    print()

    # Load manifest
    if not MANIFEST_FILE.exists():
        print(f"ERROR: Manifest not found: {MANIFEST_FILE}")
        return 1

    with MANIFEST_FILE.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Download HuggingFace tokenizers
    print("HuggingFace Tokenizers:")
    print("-" * 40)
    for repo_id, info in manifest.get("tokenizers", {}).items():
        target_dir = RESOURCES_DIR / "tokenizers" / repo_id.replace("/", "--")

        if (target_dir / "tokenizer.json").exists():
            print(f"⊙ Already downloaded: {repo_id}")
            continue

        download_hf_tokenizer(repo_id, target_dir)

    print()

    # Download SentencePiece models
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
