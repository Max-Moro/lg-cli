"""
Python comment optimization.
"""


def extract_first_sentence(text: str) -> str:
    """
    Extract the first sentence from comment text.

    Args:
        text: Comment text to process

    Returns:
        First sentence with appropriate punctuation
    """
    import re
    
    # Handle Python docstrings (triple quotes)
    if text.startswith('"""'):
        # Extract content between triple quotes
        match = re.match(r'"""\s*(.*?)\s*"""', text, re.DOTALL)
        if match:
            content = match.group(1)
        else:
            # Handle unclosed docstring or multiline
            content = text[3:].strip()
        
        sentences = re.split(r'[.!?]+', content)
        if sentences and sentences[0].strip():
            first = sentences[0].strip()
            return f'"""{first}."""'
        return text
    
    elif text.startswith("'''"):
        # Single quote Python docstring
        match = re.match(r"'''\s*(.*?)\s*'''", text, re.DOTALL)
        if match:
            content = match.group(1)
        else:
            content = text[3:].strip()
        
        sentences = re.split(r'[.!?]+', content)
        if sentences and sentences[0].strip():
            first = sentences[0].strip()
            return f"'''{first}.'''"
        return text
    
    # Handle single-line docstrings or regular strings
    elif text.startswith('"') or text.startswith("'"):
        quote = text[0]
        if text.startswith(quote * 3):
            # This case is already handled above
            return text
        
        # Single quote string
        content = text.strip(quote)
        sentences = re.split(r'[.!?]+', content)
        if sentences and sentences[0].strip():
            first = sentences[0].strip()
            return f'{quote}{first}.{quote}'
        return text
    
    # Regular comment or unquoted text
    else:
        sentences = re.split(r'[.!?]+', text)
        if sentences and sentences[0].strip():
            first = sentences[0].strip()
            return f"{first}."

    return text  # Fallback to original text

def smart_truncate_comment(comment_text: str, max_length: int) -> str:
    """
    Intelligently truncate a comment while preserving proper closing tags.

    Args:
        comment_text: Original comment text
        max_length: Maximum allowed length

    Returns:
        Properly truncated comment with correct closing tags
    """
    if len(comment_text) <= max_length:
        return comment_text

    # Python docstring patterns (triple quotes)
    if comment_text.startswith('"""'):
        # Find a good truncation point that leaves room for closing quotes
        truncate_to = max_length - 4  # Reserve space for '…"""'
        if truncate_to < 3:  # Minimum meaningful content
            return '"""…"""'

        truncated = comment_text[:truncate_to].rstrip()
        return f'{truncated}…"""'

    elif comment_text.startswith("'''"):
        # Single quote Python docstring
        truncate_to = max_length - 4  # Reserve space for "…'''"
        if truncate_to < 3:
            return "'''…'''"

        truncated = comment_text[:truncate_to].rstrip()
        return f"{truncated}…'''"

    # Single line comments
    elif comment_text.startswith('#'):
        # Simple truncation with ellipsis
        truncate_to = max_length - 1  # Reserve space for '…'
        if truncate_to < 0:
            return f"#…"

        truncated = comment_text[:truncate_to].rstrip()
        return f"{truncated}…"

    # Fallback: simple truncation
    else:
        truncate_to = max_length - 1
        if truncate_to < 0:
            return "…"

        truncated = comment_text[:truncate_to].rstrip()
        return f"{truncated}…"
