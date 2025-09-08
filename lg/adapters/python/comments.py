"""
Python comment optimization.
"""
import re


def extract_first_sentence(text: str) -> str:
    """
    Extract the first sentence from comment text.

    Args:
        text: Comment text to process

    Returns:
        First sentence with appropriate punctuation
    """
    # Remove quotes for Python docstrings
    clean_text = text.strip('"\'')

    sentences = re.split(r'[.!?]+', clean_text)
    if sentences and sentences[0].strip():
        first = sentences[0].strip()
        # Restore quotes if this is Python docstring
        if text.startswith('"""') or text.startswith("'''"):
            return f'"""{first}."""'
        elif text.startswith('"') or text.startswith("'"):
            quote = text[0]
            return f'{quote}{first}.{quote}'
        else:
            return f"{first}."

    return text  # Fallback to original text
