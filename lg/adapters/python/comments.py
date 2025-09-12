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


def _truncate_to_tokens(text: str, max_tokens: int, tokenizer) -> str:
    """
    Efficiently truncate text to fit within token budget using binary search.
    
    Args:
        text: Text to truncate
        max_tokens: Maximum allowed tokens
        tokenizer: TokenService for counting tokens
        
    Returns:
        Truncated text that fits within token budget
    """
    if tokenizer.count_text(text) <= max_tokens:
        return text
    
    # Binary search for optimal truncation point
    left, right = 0, len(text)
    best_result = ""
    
    while left <= right:
        mid = (left + right) // 2
        candidate = text[:mid].rstrip()
        token_count = tokenizer.count_text(candidate)
        
        if token_count <= max_tokens:
            best_result = candidate
            left = mid + 1
        else:
            right = mid - 1
    
    return best_result

def smart_truncate_comment(comment_text: str, max_tokens: int, tokenizer) -> str:
    """
    Intelligently truncate a comment while preserving proper closing tags.

    Args:
        comment_text: Original comment text
        max_tokens: Maximum allowed tokens
        tokenizer: TokenService for counting tokens

    Returns:
        Properly truncated comment with correct closing tags
    """
    if tokenizer.count_text(comment_text) <= max_tokens:
        return comment_text

    # Python docstring patterns (triple quotes)
    if comment_text.startswith('"""'):
        # Reserve space for closing quotes and ellipsis
        closing = '…"""'
        closing_tokens = tokenizer.count_text(closing)
        content_budget = max(1, max_tokens - closing_tokens)
        
        if content_budget < 1:
            return '"""…"""'

        # Binary search for optimal truncation point
        truncated = _truncate_to_tokens(comment_text, content_budget, tokenizer)
        return f'{truncated}…"""'

    elif comment_text.startswith("'''"):
        # Single quote Python docstring
        closing = "…'''"
        closing_tokens = tokenizer.count_text(closing)
        content_budget = max(1, max_tokens - closing_tokens)
        
        if content_budget < 1:
            return "'''…'''"

        # Binary search for optimal truncation point
        truncated = _truncate_to_tokens(comment_text, content_budget, tokenizer)
        return f"{truncated}…'''"

    # Single line comments
    elif comment_text.startswith('#'):
        # Simple truncation with ellipsis
        ellipsis_tokens = tokenizer.count_text('…')
        content_budget = max(1, max_tokens - ellipsis_tokens)
        
        if content_budget < 1:
            return f"#…"

        # Binary search for optimal truncation point
        truncated = _truncate_to_tokens(comment_text, content_budget, tokenizer)
        return f"{truncated}…"

    # Fallback: simple truncation
    else:
        ellipsis_tokens = tokenizer.count_text('…')
        content_budget = max(1, max_tokens - ellipsis_tokens)
        
        if content_budget < 1:
            return "…"

        # Binary search for optimal truncation point
        truncated = _truncate_to_tokens(comment_text, content_budget, tokenizer)
        return f"{truncated}…"
