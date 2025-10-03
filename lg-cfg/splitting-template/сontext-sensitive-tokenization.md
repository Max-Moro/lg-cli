# Оптимизация модульного лексера через контекстные группы токенов

В текущей реализации лексер работает с "плоским" списком токенов и не имеет контекстной зависимости, что может вызвать проблемы при добавлении новых плагинов.

## Текущие ограничения лексера v2

1. **Отсутствие контекстной зависимости** - лексер перебирает все токены для каждой позиции
2. **Риск коллизий** - возможны конфликты между токенами разных плагинов (например, `${...}` и `${md:...}`)
3. **Неоптимальная производительность** - каждый раз проверяются все регулярные выражения

## Предложение: контекстно-зависимая токенизация

Предлагаю реализовать систему **контекстных групп токенов**. Лексер будет отслеживать "контекст" и применять только релевантные токены.

### Основные концепции

1. **Контекстная группа токенов** - набор связанных токенов:
   - **Открывающие токены** - отмечают вход в контекст (например, `${`)
   - **Закрывающие токены** - отмечают выход из контекста (например, `}`)
   - **Внутренние токены** - допустимы только внутри контекста (например, `IDENTIFIER`, `COLON`)

2. **Стек контекстов** - лексер поддерживает стек активных контекстов для вложенных конструкций

### Реализация контекстных групп

Добавим новые структуры данных и методы:

```python
@dataclass
class TokenContext:
    """Контекст для токенизации с группами связанных токенов."""
    name: str                    # Уникальное имя контекста
    open_tokens: Set[str]        # Токены, открывающие контекст
    close_tokens: Set[str]       # Токены, закрывающие контекст
    inner_tokens: Set[str]       # Токены, допустимые только в этом контексте
    allow_nesting: bool = False  # Разрешает/запрещает вложенные контексты
    priority: int = 50           # Приоритет (для разрешения конфликтов)
```

### Обновление API регистрации в TemplateRegistry

```python
class TemplateRegistry:
    # ... существующий код ...
    
    def __init__(self):
        # ... существующий код ...
        self.token_contexts: Dict[str, TokenContext] = {}
    
    def register_token_context(self, name: str, open_tokens: List[str], 
                              close_tokens: List[str], inner_tokens: List[str] = None,
                              allow_nesting: bool = False, priority: int = 50) -> None:
        """Регистрирует новый контекст токенов."""
        if name in self.token_contexts:
            raise ValueError(f"Token context '{name}' already registered")
        
        self.token_contexts[name] = TokenContext(
            name=name,
            open_tokens=set(open_tokens),
            close_tokens=set(close_tokens),
            inner_tokens=set(inner_tokens or []),
            allow_nesting=allow_nesting,
            priority=priority
        )
    
    def register_tokens_in_context(self, context_name: str, token_names: List[str]) -> None:
        """Добавляет токены в существующий контекст."""
        if context_name not in self.token_contexts:
            raise ValueError(f"Token context '{context_name}' not found")
        
        self.token_contexts[context_name].inner_tokens.update(token_names)
```

### Модифицированный лексер

```python
class ContextualLexer:
    """Контекстно-зависимый лексический анализатор."""
    
    def __init__(self, registry: TemplateRegistry):
        self.registry = registry
        # ... существующий код ...
        self.context_stack: List[TokenContext] = []
    
    def tokenize(self, text: str) -> List[Token]:
        # ... инициализация ...
        self.context_stack = []  # Начинаем с глобального контекста
        
        tokens: List[Token] = []
        
        while self.position < self.length:
            # Получаем токены, доступные в текущем контексте
            available_specs = self._get_available_token_specs()
            
            # Находим подходящий токен
            token = self._match_next_token(available_specs)
            
            if token:
                tokens.append(token)
                # Обрабатываем изменение контекста
                self._update_context_stack(token)
            else:
                # Если не найден токен - обрабатываем как TEXT
                # ... обработка текста ...
        
        # Добавляем EOF и возвращаем результат
        # ...
    
    def _get_available_token_specs(self) -> List[TokenSpec]:
        """Возвращает спецификации токенов, доступные в текущем контексте."""
        if not self.context_stack:
            # В глобальном контексте: все открывающие токены + глобальные токены
            return self._get_global_and_opening_tokens()
        
        # В специфическом контексте: закрывающие + внутренние + возможно открывающие
        current_context = self.context_stack[-1]
        close_specs = self._get_tokens_by_names(current_context.close_tokens)
        inner_specs = self._get_tokens_by_names(current_context.inner_tokens)
        
        if current_context.allow_nesting:
            # Если разрешена вложенность, добавляем открывающие токены
            open_specs = self._get_opening_tokens_except_current()
            return close_specs + inner_specs + open_specs
        else:
            return close_specs + inner_specs
    
    def _update_context_stack(self, token: Token) -> None:
        """Обновляет стек контекстов на основе токена."""
        # Проверяем, является ли токен открывающим для какого-либо контекста
        for ctx in self.registry.token_contexts.values():
            if token.type in ctx.open_tokens:
                self.context_stack.append(ctx)
                return
        
        # Проверяем, является ли токен закрывающим для текущего контекста
        if self.context_stack and token.type in self.context_stack[-1].close_tokens:
            self.context_stack.pop()
```

### Использование в плагинах

#### Для CommonPlaceholdersPlugin:

```python
def register_token_contexts(self) -> List[Dict]:
    """Регистрирует контексты токенов для плейсхолдеров."""
    return [{
        "name": "placeholder",
        "open_tokens": ["PLACEHOLDER_START"],
        "close_tokens": ["PLACEHOLDER_END"],
        "inner_tokens": [
            "IDENTIFIER", "COLON", "AT", "LBRACKET", "RBRACKET", "WHITESPACE"
        ],
        "allow_nesting": False,
        "priority": 100
    }]
```

#### Для будущего MdPlaceholdersPlugin:

```python
def initialize(self) -> None:
    """Добавляет md-специфичные токены в контекст плейсхолдеров."""
    # Добавляем токены в существующий контекст плейсхолдеров
    self.handlers.register_tokens_in_context(
        "placeholder",  # Используем существующий контекст
        ["MD_PREFIX", "HASH", "COMMA", "LEVEL_PARAM", "STRIP_PARAM"]
    )
    
    # Регистрируем обработчик для специального префикса md:
    # ...
```

## Преимущества предложенного подхода

1. **Повышение производительности**: проверяются только токены, релевантные текущему контексту
2. **Предотвращение коллизий**: токены интерпретируются в контексте, что уменьшает ложные срабатывания
3. **Четкое разделение ответственности**: плагины могут расширять существующие контексты
4. **Обратная совместимость**: поддержка существующих плагинов
5. **Масштабируемость**: легко добавлять новые плагины без конфликтов

## План реализации

1. Добавить класс `TokenContext` для описания контекстных групп
2. Обновить `TemplateRegistry` для хранения и управления контекстами
3. Создать `ContextualLexer` для замены текущего `ModularLexer`
4. Обновить API плагинов для поддержки контекстных групп
5. Обновить существующий плагин `CommonPlaceholdersPlugin` для использования контекстов

Этот подход позволит сохранить модульность нового шаблонизатора и при этом значительно улучшит его производительность и надежность, особенно когда будут добавляться новые плагины для блоков 2 и 3.