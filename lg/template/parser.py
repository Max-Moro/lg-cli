"""
Парсер шаблонов для движка шаблонизации.

Преобразует последовательность токенов в AST (абстрактное синтаксическое дерево)
с поддержкой условных блоков, режимов, включений и плейсхолдеров секций.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .lexer import Token, TokenType, TemplateLexer
from .nodes import (
    TemplateNode, TemplateAST, TextNode, SectionNode, IncludeNode,
    ConditionalBlockNode, ElifBlockNode, ElseBlockNode, ModeBlockNode, CommentNode
)
from ..conditions.parser import ConditionParser


class ParserError(Exception):
    """Ошибка синтаксического анализа."""
    
    def __init__(self, message: str, token: Token):
        super().__init__(f"{message} at {token.line}:{token.column} (token: {token.type.name})")
        self.token = token
        self.line = token.line
        self.column = token.column


class TemplateParser:
    """
    Рекурсивный парсер для шаблонов.
    
    Обрабатывает последовательность токенов и строит AST, корректно
    обрабатывая вложенные конструкции и различные типы узлов.
    """
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.condition_parser = ConditionParser()
        
    def parse(self) -> TemplateAST:
        """
        Парсит всю последовательность токенов в AST.
        
        Returns:
            Список корневых узлов AST
            
        Raises:
            ParserError: При ошибке синтаксического анализа
        """
        ast: List[TemplateNode] = []
        
        while not self._is_at_end():
            node = self._parse_top_level()
            if node:
                ast.append(node)
        
        return ast
    
    def _parse_top_level(self) -> Optional[TemplateNode]:
        """
        Парсит узел верхнего уровня.
        
        Может быть текстом, плейсхолдером, директивой или комментарием.
        """
        if self._is_at_end():
            return None
            
        current = self._current_token()
        
        if current.type == TokenType.TEXT:
            return self._parse_text()
        elif current.type == TokenType.PLACEHOLDER_START:
            return self._parse_placeholder()
        elif current.type == TokenType.DIRECTIVE_START:
            return self._parse_directive()
        elif current.type == TokenType.COMMENT_START:
            return self._parse_comment()
        else:
            # Неожиданный токен на верхнем уровне
            raise ParserError(f"Unexpected token at top level: {current.type.name}", current)
    
    def _parse_text(self) -> TextNode:
        """Парсит текстовый узел."""
        token = self._consume(TokenType.TEXT)
        return TextNode(text=token.value)
    
    def _parse_placeholder(self) -> TemplateNode:
        """
        Парсит плейсхолдер ${...}.
        
        Может быть секцией или включением (tpl:/ctx:).
        """
        self._consume(TokenType.PLACEHOLDER_START)
        
        # Токенизируем содержимое плейсхолдера
        content_tokens = self._collect_placeholder_content()
        
        self._consume(TokenType.PLACEHOLDER_END)
        
        # Парсим содержимое плейсхолдера
        return self._parse_placeholder_content(content_tokens)
    
    def _parse_placeholder_content(self, tokens: List[Token]) -> TemplateNode:
        """
        Парсит содержимое плейсхолдера на основе токенов.
        
        Определяет тип плейсхолдера (секция или включение) и создает
        соответствующий узел.
        """
        if not tokens:
            raise ParserError("Empty placeholder", self._current_token())
        
        # Проверяем первый токен
        first_token = tokens[0]
        
        # Если начинается с @, это адресная секция
        if first_token.type == TokenType.AT:
            return self._parse_section_placeholder(tokens)
        
        # Должен быть идентификатор
        if first_token.type != TokenType.IDENTIFIER:
            raise ParserError("Expected identifier in placeholder", first_token)
        
        identifier = first_token.value
        
        # Проверяем, является ли это включением (tpl: или ctx:)
        if identifier in ('tpl', 'ctx'):
            # Может быть простое включение (tpl:name) или адресное (tpl@origin:name)
            if len(tokens) >= 3:
                if tokens[1].type == TokenType.COLON:
                    # Простое включение: tpl:name
                    return self._parse_include_placeholder(tokens)
                elif tokens[1].type == TokenType.AT:
                    # Адресное включение: tpl@origin:name
                    return self._parse_include_placeholder(tokens)
            
            raise ParserError(f"Invalid {identifier} include format", first_token)
        
        # Иначе это плейсхолдер секции
        return self._parse_section_placeholder(tokens)
    
    def _parse_section_placeholder(self, tokens: List[Token]) -> SectionNode:
        """
        Парсит плейсхолдер секции.
        
        Формат: section_name или @origin:section_name или @[origin]:section_name
        """
        if len(tokens) == 1:
            # Простая секция: ${section_name}
            section_name = tokens[0].value
            return SectionNode(section_name=section_name)
        
        # Адресная секция
        if len(tokens) >= 3 and tokens[0].type == TokenType.AT:
            section_name = self._reconstruct_section_reference(tokens)
            return SectionNode(section_name=section_name)
        
        # Fallback для неожиданных форматов
        raise ParserError(f"Invalid section placeholder format", tokens[0])
    
    def _parse_include_placeholder(self, tokens: List[Token]) -> IncludeNode:
        """
        Парсит плейсхолдер включения.
        
        Форматы:
        - tpl:name или ctx:name
        - tpl@origin:name или ctx@origin:name  
        - tpl@[origin]:name или ctx@[origin]:name
        """
        kind = tokens[0].value  # 'tpl' или 'ctx'
        
        if len(tokens) == 3 and tokens[1].type == TokenType.COLON:
            # Простое включение: tpl:name или ctx:name
            name = tokens[2].value
            return IncludeNode(kind=kind, name=name, origin="self")
        
        # Адресное включение
        if len(tokens) >= 4 and tokens[1].type == TokenType.AT:
            # Парсим адресную ссылку
            origin, name = self._parse_include_reference(tokens[1:])  # Пропускаем kind
            return IncludeNode(kind=kind, name=name, origin=origin)
        
        raise ParserError(f"Invalid {kind} include format", tokens[0])
    
    def _parse_directive(self) -> TemplateNode:
        """
        Парсит директиву {% ... %}.
        
        Может быть условием (if), режимом (mode) или их завершением.
        """
        self._consume(TokenType.DIRECTIVE_START)
        
        # Токенизируем содержимое директивы
        content_tokens = self._collect_directive_content()
        
        self._consume(TokenType.DIRECTIVE_END)
        
        # Парсим содержимое директивы
        return self._parse_directive_content(content_tokens)
    
    def _parse_directive_content(self, tokens: List[Token]) -> TemplateNode:
        """
        Парсит содержимое директивы на основе токенов.
        """
        if not tokens:
            raise ParserError("Empty directive", self._current_token())
        
        first_token = tokens[0]
        
        if first_token.type == TokenType.IF:
            return self._parse_if_directive(tokens)
        elif first_token.type == TokenType.ELIF:
            raise ParserError("elif without if", first_token)
        elif first_token.type == TokenType.ELSE:
            return self._parse_else_directive(tokens)
        elif first_token.type == TokenType.MODE:
            return self._parse_mode_directive(tokens)
        elif first_token.type == TokenType.ENDIF:
            raise ParserError("endif without if", first_token)
        elif first_token.type == TokenType.ENDMODE:
            raise ParserError("endmode without mode", first_token)
        else:
            raise ParserError(f"Unknown directive: {first_token.value}", first_token)
    
    def _parse_if_directive(self, tokens: List[Token]) -> ConditionalBlockNode:
        """
        Парсит условную директиву {% if condition %} с поддержкой elif.
        
        Включает обработку тела условия, опциональных elif блоков и else блока.
        """
        # Извлекаем условие (все токены после 'if')
        if len(tokens) < 2:
            raise ParserError("Missing condition in if directive", tokens[0])
        
        condition_tokens = tokens[1:]
        condition_text = self._reconstruct_condition_text(condition_tokens)
        
        # Парсим условие с помощью парсера условий
        try:
            condition_ast = self.condition_parser.parse(condition_text)
        except Exception as e:
            raise ParserError(f"Invalid condition: {e}", tokens[0])
        
        # Парсим тело условия до elif, else или endif
        body_nodes = []
        elif_blocks = []
        else_block = None
        found_end = False
        
        while not self._is_at_end():
            # Проверяем, не встретили ли мы endif, elif или else
            if self._check_directive_keyword(TokenType.ENDIF):
                self._consume_directive_keyword(TokenType.ENDIF)
                found_end = True
                break
            elif self._check_directive_keyword(TokenType.ELIF):
                # Парсим elif блоки
                elif_blocks.extend(self._parse_elif_blocks())
                # После парсинга всех elif блоков проверяем else
                if self._check_directive_keyword(TokenType.ELSE):
                    self._consume_directive_keyword(TokenType.ELSE)
                    else_block = self._parse_else_block()
                self._consume_directive_keyword(TokenType.ENDIF)
                found_end = True
                break
            elif self._check_directive_keyword(TokenType.ELSE):
                self._consume_directive_keyword(TokenType.ELSE)
                else_block = self._parse_else_block()
                self._consume_directive_keyword(TokenType.ENDIF)
                found_end = True
                break
            
            node = self._parse_top_level()
            if node:
                body_nodes.append(node)
        
        if not found_end:
            raise ParserError("Unexpected end of tokens, expected {% endif %}", tokens[0])
        
        return ConditionalBlockNode(
            condition_text=condition_text,
            body=body_nodes,
            elif_blocks=elif_blocks,
            else_block=else_block,
            condition_ast=condition_ast
        )
    
    def _parse_elif_blocks(self) -> List[ElifBlockNode]:
        """
        Парсит последовательность elif блоков.
        
        Возвращает список ElifBlockNode до тех пор, пока не встретит
        else, endif или конец токенов.
        """
        elif_blocks = []
        
        while self._check_directive_keyword(TokenType.ELIF):
            self._consume(TokenType.DIRECTIVE_START)  # {%
            
            # Токенизируем содержимое elif директивы
            content_tokens = self._collect_directive_content()
            
            self._consume(TokenType.DIRECTIVE_END)    # %}
            
            # Парсим содержимое elif директивы
            elif_block = self._parse_single_elif_directive(content_tokens)
            elif_blocks.append(elif_block)
        
        return elif_blocks
    
    def _parse_single_elif_directive(self, tokens: List[Token]) -> ElifBlockNode:
        """
        Парсит одну elif директиву из уже извлеченных токенов содержимого.
        """
        if not tokens or tokens[0].value != 'elif':
            raise ParserError("Expected 'elif' keyword", tokens[0] if tokens else self._current_token())
        
        # Извлекаем условие (все токены после 'elif')
        if len(tokens) < 2:
            raise ParserError("Missing condition in elif directive", tokens[0])
        
        condition_tokens = tokens[1:]
        condition_text = self._reconstruct_condition_text(condition_tokens)
        
        # Парсим условие с помощью парсера условий
        try:
            condition_ast = self.condition_parser.parse(condition_text)
        except Exception as e:
            raise ParserError(f"Invalid elif condition: {e}", tokens[0])
        
        # Парсим тело elif блока
        elif_body = []
        while not self._is_at_end():
            if (self._check_directive_keyword(TokenType.ELIF) or 
                self._check_directive_keyword(TokenType.ELSE) or 
                self._check_directive_keyword(TokenType.ENDIF)):
                break
            
            node = self._parse_top_level()
            if node:
                elif_body.append(node)
        
        return ElifBlockNode(
            condition_text=condition_text,
            body=elif_body,
            condition_ast=condition_ast
        )
    
    def _parse_else_directive(self, tokens: List[Token]) -> ElseBlockNode:
        """
        Парсит else директиву (используется внутри if блоков).
        
        Примечание: Этот метод не должен вызываться напрямую,
        else обрабатывается внутри _parse_if_directive.
        """
        raise ParserError("else without if", tokens[0])
    
    def _parse_else_block(self) -> ElseBlockNode:
        """Парсит тело else блока до endif."""
        body_nodes = []
        
        while not self._is_at_end():
            if self._check_directive_keyword(TokenType.ENDIF):
                break
            
            node = self._parse_top_level()
            if node:
                body_nodes.append(node)
        
        return ElseBlockNode(body=body_nodes)
    
    def _parse_mode_directive(self, tokens: List[Token]) -> ModeBlockNode:
        """
        Парсит директиву режима {% mode modeset:mode %}.
        """
        if len(tokens) < 4:  # mode, modeset, :, mode_name
            raise ParserError("Missing mode specification", tokens[0])
        
        # Ожидаем format: mode modeset : mode_name
        if tokens[1].type != TokenType.IDENTIFIER or tokens[2].type != TokenType.COLON or tokens[3].type != TokenType.IDENTIFIER:
            raise ParserError("Invalid mode format, expected 'modeset:mode'", tokens[1])
        
        modeset = tokens[1].value
        mode = tokens[3].value
        
        # Парсим тело режима до endmode
        body_nodes = []
        found_end = False
        
        while not self._is_at_end():
            if self._check_directive_keyword(TokenType.ENDMODE):
                self._consume_directive_keyword(TokenType.ENDMODE)
                found_end = True
                break
            
            node = self._parse_top_level()
            if node:
                body_nodes.append(node)
        
        if not found_end:
            raise ParserError("Unexpected end of tokens, expected {% endmode %}", tokens[0])
        
        return ModeBlockNode(modeset=modeset, mode=mode, body=body_nodes)
    
    def _parse_comment(self) -> CommentNode:
        """Парсит комментарий {# ... #}."""
        self._consume(TokenType.COMMENT_START)
        
        # Собираем все содержимое до #}
        content_parts = []
        
        while not self._is_at_end():
            current = self._current_token()
            if current.type == TokenType.COMMENT_END:
                break
            content_parts.append(current.value)
            self._advance()
        
        self._consume(TokenType.COMMENT_END)
        
        return CommentNode(text=''.join(content_parts))
    
    # Вспомогательные методы для адресных ссылок
    
    def _reconstruct_section_reference(self, tokens: List[Token]) -> str:
        """
        Восстанавливает полную адресную ссылку на секцию из токенов.
        
        Поддерживает форматы:
        - @origin:name
        - @[origin]:name
        """
        if not tokens:
            raise ParserError("Empty section reference", self._current_token())
        if tokens[0].type != TokenType.AT:
            raise ParserError("Expected '@' at start of section reference", tokens[0])
        
        if len(tokens) >= 4 and tokens[1].type == TokenType.LBRACKET:
            # Формат: @[origin]:name
            return self._reconstruct_bracketed_reference(tokens)
        else:
            # Формат: @origin:name
            return self._reconstruct_simple_reference(tokens)
    
    def _reconstruct_bracketed_reference(self, tokens: List[Token]) -> str:
        """Восстанавливает ссылку вида @[origin]:name."""
        # Ожидаем: @ [ origin ] : name
        if len(tokens) < 5:
            raise ParserError("Incomplete bracketed reference", tokens[0])
        
        if (tokens[0].type != TokenType.AT or 
            tokens[1].type != TokenType.LBRACKET):
            raise ParserError("Invalid bracketed reference format", tokens[0])
        
        # Находим закрывающую скобку
        bracket_end = -1
        for i in range(2, len(tokens)):
            if tokens[i].type == TokenType.RBRACKET:
                bracket_end = i
                break
        
        if bracket_end == -1:
            raise ParserError("Missing closing bracket in reference", tokens[1])
        
        # Проверяем двоеточие после скобки
        if (bracket_end + 1 >= len(tokens) or 
            tokens[bracket_end + 1].type != TokenType.COLON):
            raise ParserError("Missing ':' after bracketed origin", tokens[bracket_end] if bracket_end < len(tokens) else tokens[-1])
        
        # Собираем origin (между скобками)
        origin_parts = []
        for i in range(2, bracket_end):
            origin_parts.append(tokens[i].value)
        origin = ''.join(origin_parts)
        
        # Собираем name (после двоеточия)  
        name_parts = []
        for i in range(bracket_end + 2, len(tokens)):
            name_parts.append(tokens[i].value)
        name = ''.join(name_parts)
        
        return f"@[{origin}]:{name}"
    
    def _reconstruct_simple_reference(self, tokens: List[Token]) -> str:
        """Восстанавливает ссылку вида @origin:name."""
        # Ожидаем: @ origin : name
        if len(tokens) < 3:
            raise ParserError("Incomplete simple reference", tokens[0])
        
        # Находим двоеточие
        colon_pos = -1
        for i in range(1, len(tokens)):
            if tokens[i].type == TokenType.COLON:
                colon_pos = i
                break
        
        if colon_pos == -1:
            raise ParserError("Missing ':' in reference", tokens[0])
        
        # Собираем origin (между @ и :)
        origin_parts = []
        for i in range(1, colon_pos):
            origin_parts.append(tokens[i].value)
        origin = ''.join(origin_parts)
        
        # Собираем name (после :)
        name_parts = []
        for i in range(colon_pos + 1, len(tokens)):
            name_parts.append(tokens[i].value)
        name = ''.join(name_parts)
        
        return f"@{origin}:{name}"
    
    def _parse_include_reference(self, tokens: List[Token]) -> Tuple[str, str]:
        """
        Парсит адресную ссылку включения и возвращает (origin, name).
        
        Поддерживает форматы:
        - @origin:name  
        - @[origin]:name
        """
        full_ref = self._reconstruct_section_reference(tokens)
        
        # Парсим результат для извлечения origin и name
        if full_ref.startswith("@["):
            # @[origin]:name
            close = full_ref.find("]:")
            if close < 0:
                raise ParserError(f"Invalid bracketed reference: {full_ref}", tokens[0])
            origin = full_ref[2:close]
            name = full_ref[close + 2:]
        else:
            # @origin:name
            colon = full_ref.find(":", 1)  # Ищем после @
            if colon < 0:
                raise ParserError(f"Invalid simple reference: {full_ref}", tokens[0])
            origin = full_ref[1:colon]
            name = full_ref[colon + 1:]
        
        return origin, name
    
    # Вспомогательные методы
    
    def _collect_placeholder_content(self) -> List[Token]:
        """Собирает токены содержимого плейсхолдера до }."""
        content_parts = []
        
        while not self._is_at_end():
            current = self._current_token()
            if current.type == TokenType.PLACEHOLDER_END:
                break
            content_parts.append(current.value)
            self._advance()
        
        # Токенизируем собранное содержимое
        content_text = ''.join(content_parts)
        if content_text.strip():
            # Создаем новый лексер и используем правильный метод токенизации
            temp_lexer = TemplateLexer(content_text)
            tokens = []
            
            while temp_lexer.position < temp_lexer.length:
                token = temp_lexer._tokenize_inside_placeholder()
                if token.type == TokenType.EOF:
                    break
                tokens.append(token)
            
            return tokens
        else:
            return []
    
    def _collect_directive_content(self) -> List[Token]:
        """Собирает токены содержимого директивы до %}."""
        content_parts = []
        
        while not self._is_at_end():
            current = self._current_token()
            if current.type == TokenType.DIRECTIVE_END:
                break
            content_parts.append(current.value)
            self._advance()
        
        # Токенизируем собранное содержимое
        content_text = ''.join(content_parts).strip()
        if content_text:
            # Создаем новый лексер для содержимого директивы
            lexer = TemplateLexer(content_text)
            tokens = []
            
            while lexer.position < lexer.length:
                token = lexer._tokenize_inside_directive()
                if token.type == TokenType.EOF:
                    break
                tokens.append(token)
            
            return tokens
        else:
            return []
    
    def _reconstruct_condition_text(self, tokens: List[Token]) -> str:
        """Восстанавливает текст условия из токенов."""
        return ' '.join(token.value for token in tokens)
    
    def _check_directive_keyword(self, keyword: TokenType) -> bool:
        """
        Проверяет, следует ли указанное ключевое слово директивы.
        
        Заглядывает вперед, чтобы проверить наличие {% keyword %}.
        """
        if (self.position + 2 < len(self.tokens) and
            self.tokens[self.position].type == TokenType.DIRECTIVE_START and
            self.tokens[self.position + 2].type == TokenType.DIRECTIVE_END):
            # Проверяем содержимое директивы
            content = self.tokens[self.position + 1].value.strip()
            # Сопоставляем токены с их строковыми представлениями
            keyword_map = {
                TokenType.IF: "if",
                TokenType.ELIF: "elif",
                TokenType.ELSE: "else", 
                TokenType.ENDIF: "endif",
                TokenType.MODE: "mode",
                TokenType.ENDMODE: "endmode"
            }
            expected_keyword = keyword_map.get(keyword, keyword.name.lower())
            # Для директив с параметрами проверяем только начало
            if keyword in [TokenType.IF, TokenType.ELIF, TokenType.MODE]:
                return content.startswith(expected_keyword + ' ') or content == expected_keyword
            else:
                # Для директив без параметров проверяем точное соответствие
                return content == expected_keyword
        return False
    
    def _consume_directive_keyword(self, keyword: TokenType) -> None:
        """Потребляет директиву с указанным ключевым словом."""
        self._consume(TokenType.DIRECTIVE_START)
        # Проверяем, что содержимое соответствует ключевому слову
        content_token = self._current_token()
        # Сопоставляем токены с их строковыми представлениями
        keyword_map = {
            TokenType.IF: "if",
            TokenType.ELIF: "elif",
            TokenType.ELSE: "else",
            TokenType.ENDIF: "endif", 
            TokenType.MODE: "mode",
            TokenType.ENDMODE: "endmode"
        }
        expected_keyword = keyword_map.get(keyword, keyword.name.lower())
        content = content_token.value.strip()
        # Для директив с параметрами проверяем только начало
        if keyword in [TokenType.IF, TokenType.ELIF, TokenType.MODE]:
            if not (content.startswith(expected_keyword + ' ') or content == expected_keyword):
                raise ParserError(f"Expected directive starting with '{expected_keyword}', got '{content}'", content_token)
        else:
            # Для директив без параметров проверяем точное соответствие
            if content != expected_keyword:
                raise ParserError(f"Expected '{expected_keyword}', got '{content}'", content_token)
        self._advance()  # Потребляем содержимое
        self._consume(TokenType.DIRECTIVE_END)
    
    def _current_token(self) -> Token:
        """Возвращает текущий токен."""
        if self.position >= len(self.tokens):
            # Возвращаем EOF токен если достигли конца
            last_token = self.tokens[-1] if self.tokens else Token(TokenType.EOF, "", 0, 1, 1)
            return Token(TokenType.EOF, "", last_token.position, last_token.line, last_token.column)
        return self.tokens[self.position]
    
    def _advance(self) -> Token:
        """Продвигается к следующему токену и возвращает предыдущий."""
        current = self._current_token()
        if not self._is_at_end():
            self.position += 1
        return current
    
    def _is_at_end(self) -> bool:
        """Проверяет, достигли ли мы конца токенов."""
        return (self.position >= len(self.tokens) or 
                self._current_token().type == TokenType.EOF)
    
    def _consume(self, expected_type: TokenType) -> Token:
        """
        Потребляет токен ожидаемого типа.
        
        Raises:
            ParserError: Если токен не соответствует ожидаемому типу
        """
        current = self._current_token()
        if current.type != expected_type:
            raise ParserError(
                f"Expected {expected_type.name}, got {current.type.name}", 
                current
            )
        return self._advance()


def parse_template(text: str) -> TemplateAST:
    """
    Удобная функция для парсинга шаблона из текста.
    
    Args:
        text: Исходный текст шаблона
        
    Returns:
        AST шаблона
        
    Raises:
        LexerError: При ошибке лексического анализа
        ParserError: При ошибке синтаксического анализа
    """
    lexer = TemplateLexer(text)
    tokens = lexer.tokenize()
    
    parser = TemplateParser(tokens)
    return parser.parse()
