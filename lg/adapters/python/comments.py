"""
Python comment optimization.
"""
from lg.adapters.tree_sitter_support import TreeSitterDocument


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

        # Truncate using tokenizer
        truncated = tokenizer.truncate_to_tokens(comment_text, content_budget)
        return f'{truncated}…"""'

    elif comment_text.startswith("'''"):
        # Single quote Python docstring
        closing = "…'''"
        closing_tokens = tokenizer.count_text(closing)
        content_budget = max(1, max_tokens - closing_tokens)
        
        if content_budget < 1:
            return "'''…'''"

        # Truncate using tokenizer
        truncated = tokenizer.truncate_to_tokens(comment_text, content_budget)
        return f"{truncated}…'''"

    # Single line comments
    elif comment_text.startswith('#'):
        # Simple truncation with ellipsis
        ellipsis_tokens = tokenizer.count_text('…')
        content_budget = max(1, max_tokens - ellipsis_tokens)
        
        if content_budget < 1:
            return f"#…"

        # Truncate using tokenizer
        truncated = tokenizer.truncate_to_tokens(comment_text, content_budget)
        return f"{truncated}…"

    # Fallback: simple truncation
    else:
        ellipsis_tokens = tokenizer.count_text('…')
        content_budget = max(1, max_tokens - ellipsis_tokens)
        
        if content_budget < 1:
            return "…"

        # Truncate using tokenizer
        truncated = tokenizer.truncate_to_tokens(comment_text, content_budget)
        return f"{truncated}…"

def is_docstring_node(node, doc: TreeSitterDocument) -> bool:
    """
    Проверяет, является ли узел строки докстрингом.
    
    В Python докстрингом считается строка, которая является единственным содержимым
    expression_statement. Это соответствует запросу comments в queries.py.

    Args:
        node: Узел строки для проверки
        doc: Документ для анализа контекста

    Returns:
        True если узел является докстрингом, False иначе
    """
    # Проверяем, является ли родительский узел expression_statement
    # и содержит ли он только эту строку (без других выражений)
    parent = node.parent
    if parent and parent.type == "expression_statement":
        # Если expression_statement содержит только одну строку, это докстринг
        if len(parent.children) == 1:
            return True
    
    return False
