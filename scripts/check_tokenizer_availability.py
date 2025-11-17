#!/usr/bin/env python3
"""
Checks availability of HuggingFace tokenizers for anonymous download.

Usage:
    python scripts/check_tokenizer_availability.py
"""

from huggingface_hub import list_repo_files, hf_hub_download
import tempfile

# Candidates for checking
TOKENIZERS_CANDIDATES = [
    # Current recommended
    "gpt2",
    "roberta-base",
    "bert-base-uncased",
    "bert-base-cased",
    "t5-base",
    "google/gemma-tokenizer",

    # Additional candidates
    "facebook/opt-125m",
    "EleutherAI/gpt-neo-125m",
    "EleutherAI/gpt-j-6b",
    "bigscience/bloom-560m",
    "google/flan-t5-base",
    "microsoft/phi-2",
    "mistralai/Mistral-7B-v0.1",
]

SENTENCEPIECE_CANDIDATES = [
    # Current recommended
    "google/gemma-2-2b",
    "meta-llama/Llama-2-7b-hf",

    # Additional candidates
    "t5-small",
    "t5-base",
    "google/flan-t5-base",
    "facebook/mbart-large-50",
    "xlnet-base-cased",
    "google/mt5-base",
]

def check_tokenizer(repo_id: str, verbose: bool = True) -> dict:
    """
    Checks availability of tokenizers model.

    Returns:
        dict with fields:
        - available: bool
        - has_tokenizer_json: bool
        - error: str | None
        - files: list[str] | None
    """
    result = {
        "repo_id": repo_id,
        "available": False,
        "has_tokenizer_json": False,
        "error": None,
        "files": None,
    }
    
    try:
        # Check list of files
        files = list_repo_files(repo_id)
        result["files"] = [f for f in files if "tokenizer" in f.lower()]

        if "tokenizer.json" in files:
            result["has_tokenizer_json"] = True

            # Try to download
            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    _ = hf_hub_download(
                        repo_id=repo_id,
                        filename="tokenizer.json",
                        cache_dir=tmpdir,
                        local_dir=tmpdir,
                        local_dir_use_symlinks=False,
                    )
                    result["available"] = True
                    if verbose:
                        print(f"✓ {repo_id}: Successfully downloaded tokenizer.json")
                except Exception as e:
                    result["error"] = str(e)
                    if verbose:
                        print(f"✗ {repo_id}: Failed to download - {e}")
        else:
            result["error"] = "No tokenizer.json found"
            if verbose:
                print(f"⊙ {repo_id}: No tokenizer.json (files: {result['files']})")
    
    except Exception as e:
        result["error"] = str(e)
        if verbose:
            print(f"✗ {repo_id}: Error accessing repo - {e}")
    
    return result


def check_sentencepiece(repo_id: str, verbose: bool = True) -> dict:
    """
    Checks availability of SentencePiece model.

    Returns:
        dict with fields:
        - available: bool
        - found_file: str | None (which file was found)
        - error: str | None
        - files: list[str] | None
    """
    result = {
        "repo_id": repo_id,
        "available": False,
        "found_file": None,
        "error": None,
        "files": None,
    }
    
    try:
        # Check list of files
        files = list_repo_files(repo_id)
        result["files"] = [f for f in files if f.endswith(('.model', '.spm'))]

        # Try standard names
        filenames_to_try = ["tokenizer.model", "spiece.model", "sentencepiece.model"]

        for filename in filenames_to_try:
            if filename in files:
                # Try to download
                with tempfile.TemporaryDirectory() as tmpdir:
                    try:
                        _ = hf_hub_download(
                            repo_id=repo_id,
                            filename=filename,
                            cache_dir=tmpdir,
                            local_dir=tmpdir,
                            local_dir_use_symlinks=False,
                        )
                        result["available"] = True
                        result["found_file"] = filename
                        if verbose:
                            print(f"✓ {repo_id}: Successfully downloaded {filename}")
                        return result
                    except Exception as e:
                        result["error"] = str(e)
                        if verbose:
                            print(f"✗ {repo_id}: Failed to download {filename} - {e}")
                        continue
        
        if not result["available"]:
            result["error"] = f"No SentencePiece model found. Available .model files: {result['files']}"
            if verbose:
                print(f"⊙ {repo_id}: No standard SentencePiece file (files: {result['files']})")
    
    except Exception as e:
        result["error"] = str(e)
        if verbose:
            print(f"✗ {repo_id}: Error accessing repo - {e}")
    
    return result


def main():
    print("=" * 60)
    print("Checking HuggingFace Tokenizers availability")
    print("=" * 60)
    print()
    
    print("HuggingFace Tokenizers (tokenizer.json):")
    print("-" * 60)
    tokenizers_results = []
    for repo_id in TOKENIZERS_CANDIDATES:
        result = check_tokenizer(repo_id, verbose=True)
        tokenizers_results.append(result)
    
    print()
    print("SentencePiece Models (.model files):")
    print("-" * 60)
    sp_results = []
    for repo_id in SENTENCEPIECE_CANDIDATES:
        result = check_sentencepiece(repo_id, verbose=True)
        sp_results.append(result)
    
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    print()
    print("✅ Available Tokenizers:")
    available_tokenizers = [r for r in tokenizers_results if r["available"]]
    if available_tokenizers:
        for r in available_tokenizers:
            print(f"  - {r['repo_id']}")
    else:
        print("  (none)")
    
    print()
    print("✅ Available SentencePiece:")
    available_sp = [r for r in sp_results if r["available"]]
    if available_sp:
        for r in available_sp:
            print(f"  - {r['repo_id']} (file: {r['found_file']})")
    else:
        print("  (none)")
    
    print()
    print("❌ Unavailable Tokenizers:")
    unavailable_tokenizers = [r for r in tokenizers_results if not r["available"]]
    if unavailable_tokenizers:
        for r in unavailable_tokenizers:
            print(f"  - {r['repo_id']}: {r['error']}")
    else:
        print("  (none)")
    
    print()
    print("❌ Unavailable SentencePiece:")
    unavailable_sp = [r for r in sp_results if not r["available"]]
    if unavailable_sp:
        for r in unavailable_sp:
            print(f"  - {r['repo_id']}: {r['error']}")
    else:
        print("  (none)")
    
    print()
    print("=" * 60)
    print("Recommendations for code updates:")
    print("=" * 60)
    
    print()
    print("RECOMMENDED_TOKENIZERS = [")
    for r in available_tokenizers:
        print(f'    "{r["repo_id"]}",')
    print("]")
    
    print()
    print("RECOMMENDED_MODELS = [  # SentencePiece")
    for r in available_sp:
        print(f'    "{r["repo_id"]}",  # {r["found_file"]}')
    print("]")


if __name__ == "__main__":
    main()
