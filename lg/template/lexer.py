"""
Context-sensitive lexical analyzer for modular template engine.

Uses contextual token groups for efficient tokenization
and collision prevention between plugins.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .registry import TemplateRegistry
from .tokens import Token, TokenType
from .types import TokenSpec, TokenContext


class ContextualLexer:
    """
    Context-sensitive lexical analyzer.

    Tracks active contexts and applies only relevant tokens,
    improving performance and preventing collisions.
    """

    def __init__(self, registry: TemplateRegistry):
        """
        Initializes lexer with plugin registry.

        Args:
            registry: Registry with registered tokens and contexts
        """
        self.registry = registry

        # Position information
        self.text = ""
        self.position = 0
        self.line = 1
        self.column = 1
        self.length = 0

        # Stack of active contexts for nested constructs
        self.context_stack: List[TokenContext] = []

        # Cached token specifications
        self._global_token_cache: Optional[List[TokenSpec]] = None
        self._context_token_cache: Dict[str, List[TokenSpec]] = {}

    def tokenize(self, text: str) -> List[Token]:
        """
        Context-sensitive tokenization.

        Applies only relevant tokens based on current context,
        automatically handling context entries and exits.

        Args:
            text: Source text to tokenize

        Returns:
            List of tokens

        Raises:
            LexerError: If tokenization error occurs
        """
        self._initialize_tokenization(text)

        tokens: List[Token] = []

        while self.position < self.length:
            token = self._match_next_token()

            if token is None:
                # Failed to find matching token - handle as text
                token = self._handle_unparsed_content()

            if token and token.value:  # Skip tokens with empty content
                tokens.append(token)
                self._update_context_stack(token)

        # Add EOF token
        tokens.append(Token(TokenType.EOF.value, "", self.position, self.line, self.column))

        return tokens

    def _initialize_tokenization(self, text: str) -> None:
        """Initializes state for new tokenization."""
        self.text = text
        self.position = 0
        self.line = 1
        self.column = 1
        self.length = len(text)
        self.context_stack = []

        # Clear context token caches
        self._context_token_cache.clear()

    def _match_next_token(self) -> Optional[Token]:
        """
        Attempts to find matching token at current position.

        Uses context filtering for performance optimization
        and preventing false matches.

        Returns:
            Found token or None
        """
        start_line, start_column = self.line, self.column
        start_position = self.position

        # Get tokens available in current context
        available_specs = self._get_available_token_specs()

        # Try each token specification in priority order
        for spec in available_specs:
            match = spec.pattern.match(self.text, self.position)
            if match:
                matched_text = match.group(0)
                self._advance(len(matched_text))
                
                token = Token(
                    spec.name,
                    matched_text,
                    start_position,
                    start_line,
                    start_column
                )
                
                return token
        
        return None
    
    def _get_available_token_specs(self) -> List[TokenSpec]:
        """
        Returns token specifications available in current context.

        Uses caching for performance improvement.

        Returns:
            Filtered and sorted list of tokens
        """
        if not self.context_stack:
            # In global context: cache global tokens
            return self._get_global_tokens()

        # In specific context: use cache for context
        current_context = self.context_stack[-1]
        context_key = f"{current_context.name}_{len(self.context_stack)}"

        if context_key not in self._context_token_cache:
            self._context_token_cache[context_key] = self._build_context_tokens(current_context)

        return self._context_token_cache[context_key]
    
    def _get_global_tokens(self) -> List[TokenSpec]:
        """
        Returns tokens for global context with caching.

        Returns:
            List of global tokens and context opening tokens
        """
        if self._global_token_cache is None:
            # Get all registered tokens
            all_tokens = self.registry.get_tokens_by_priority()

            # In global context available:
            # 1. Global tokens (TEXT, EOF, etc.)
            # 2. Opening tokens of all contexts
            global_tokens = []
            opening_tokens = set()

            # Collect opening tokens from all contexts
            for context in self.registry.get_all_token_contexts():
                opening_tokens.update(context.open_tokens)

            # Filter tokens
            for token_spec in all_tokens:
                # Include if token:
                # - is global (TEXT, EOF, and other base tokens)
                # - or is opening token for some context
                if self._is_global_token(token_spec) or token_spec.name in opening_tokens:
                    global_tokens.append(token_spec)

            self._global_token_cache = global_tokens

        return self._global_token_cache
    
    def _build_context_tokens(self, context: TokenContext) -> List[TokenSpec]:
        """
        Builds list of tokens for specified context.

        Args:
            context: Context for building token list

        Returns:
            Sorted list of tokens for context
        """
        all_tokens = self.registry.get_tokens_by_priority()
        context_tokens = []

        # Define available token names for context
        available_token_names = set()

        # 1. Context closing tokens (always available)
        available_token_names.update(context.close_tokens)

        # 2. Context inner tokens
        available_token_names.update(context.inner_tokens)

        # 3. If nesting allowed, add opening tokens of other contexts
        if context.allow_nesting:
            for other_context in self.registry.get_all_token_contexts():
                if other_context.name != context.name:  # Exclude current context
                    available_token_names.update(other_context.open_tokens)

        # Filter tokens by available names
        for token_spec in all_tokens:
            if token_spec.name in available_token_names:
                context_tokens.append(token_spec)

        return context_tokens
    
    def _is_global_token(self, token_spec: TokenSpec) -> bool:
        """
        Checks if token is global.

        Global tokens are available outside all contexts.

        Args:
            token_spec: Token specification

        Returns:
            True if token is global
        """
        # Base global tokens
        global_token_names = {TokenType.TEXT.value, TokenType.EOF.value}

        return token_spec.name in global_token_names
    
    def _update_context_stack(self, token: Token) -> None:
        """
        Updates context stack based on token.

        Args:
            token: Token that may change context
        """
        # Check if token is closing for current context
        if self.context_stack and token.type in self.context_stack[-1].close_tokens:
            self.context_stack.pop()

            # Clear cache for closed context
            self._invalidate_context_cache()
            return

        # Check if token is opening for some context
        for context in self.registry.get_all_token_contexts():
            if token.type in context.open_tokens:
                self.context_stack.append(context)
                # Clear cache for new context
                self._invalidate_context_cache()
                return

    def _invalidate_context_cache(self) -> None:
        """Clears context token cache when context stack changes."""
        self._context_token_cache.clear()

    def _get_context_name(self) -> str:
        """Returns current context name for logging."""
        if not self.context_stack:
            return "global"
        return self.context_stack[-1].name
    
    def _handle_unparsed_content(self) -> Token:
        """
        Handles content that failed to parse as special token.

        Collects continuous text until next potential special token.

        Returns:
            TEXT token with collected content
        """
        start_line, start_column = self.line, self.column
        start_position = self.position

        # Collect characters until next potential special token
        collected_text = ""

        while self.position < self.length:
            # Check if current position could start special token
            if self._could_be_special_token_start():
                break

            # Add character to text
            collected_text += self.text[self.position]
            self._advance(1)

        # If collected nothing, take at least one char to avoid infinite loop
        if not collected_text and self.position < self.length:
            collected_text = self.text[self.position]
            self._advance(1)

        token = Token(
            TokenType.TEXT.value,
            collected_text,
            start_position,
            start_line,
            start_column
        )

        return token
    
    def _could_be_special_token_start(self) -> bool:
        """
        Checks if current position could start special token.

        Used for optimization of TEXT token collection.

        Returns:
            True if special token could start at current position
        """
        if self.position >= self.length:
            return False

        # Get tokens available for current context
        available_specs = self._get_available_token_specs()

        # Check if any token could start at current position
        for spec in available_specs:
            if spec.name == TokenType.TEXT.value:  # Skip TEXT token
                continue

            # Check only pattern start for optimization
            if spec.pattern.match(self.text, self.position):
                return True

        return False

    def _advance(self, count: int) -> None:
        """
        Advances position by specified number of characters.

        Updates line and column numbers for proper position tracking.

        Args:
            count: Number of characters to advance
        """
        for _ in range(count):
            if self.position >= self.length:
                break

            char = self.text[self.position]
            if char == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1

            self.position += 1


__all__ = ["ContextualLexer"]