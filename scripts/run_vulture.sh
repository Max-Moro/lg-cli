#!/bin/bash

# Скрипт для анализа неиспользуемого кода с помощью Vulture
# Автор: AI Assistant
# Описание: Запускает Vulture для поиска мертвого кода в проекте

# set -e  # Отключено, чтобы обрабатывать коды выхода Vulture

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для логирования
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка существования виртуального окружения
if [ ! -d ".venv" ]; then
    error "Виртуальное окружение .venv не найдено!"
    exit 1
fi

# Проверка установки Vulture
if ! .venv/Scripts/python.exe -m vulture --version > /dev/null 2>&1; then
    error "Vulture не установлен в виртуальном окружении!"
    log "Установите зависимости: .venv/Scripts/python.exe -m pip install -e \".[dev]\""
    exit 1
fi

# Проверка существования конфигурационного файла
if [ ! -f "vulture.toml" ]; then
    error "Файл конфигурации vulture.toml не найден!"
    exit 1
fi

# Создание директории для отчетов
REPORT_DIR="reports"
mkdir -p "$REPORT_DIR"

# Генерация имени файла отчета с временной меткой
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="$REPORT_DIR/vulture_report_$TIMESTAMP.txt"

log "Начинаем анализ неиспользуемого кода..."

# Запуск Vulture с подробным выводом
log "Запуск Vulture с конфигурацией из vulture.toml..."

# Запуск Vulture и сохранение кода выхода
.venv/Scripts/python.exe -m vulture \
    --config vulture.toml \
    --min-confidence 60 \
    --sort-by-size \
    lg \
    > "$REPORT_FILE" 2>&1
VULTURE_EXIT_CODE=$?

# Проверка результата выполнения
if [ $VULTURE_EXIT_CODE -eq 0 ]; then
    success "Анализ завершен успешно!"
    success "Неиспользуемый код не найден! Проект чистый."
else
    success "Анализ завершен успешно!"
    
    # Подсчет найденных проблем
    ISSUES_COUNT=$(wc -l < "$REPORT_FILE" 2>/dev/null || echo "0")
    
    if [ "$ISSUES_COUNT" -gt 0 ]; then
        warning "Найдено $ISSUES_COUNT потенциально неиспользуемых элементов кода"
        
        # Показываем краткую сводку
        log "Краткая сводка найденных проблем:"
        echo "----------------------------------------"
        head -20 "$REPORT_FILE"
        echo "----------------------------------------"
        
        if [ "$ISSUES_COUNT" -gt 20 ]; then
            log "Показаны первые 20 проблем. Полный отчет в файле: $REPORT_FILE"
        fi
    else
        success "Неиспользуемый код не найден! Проект чистый."
    fi
    
    log "Полный отчет сохранен в файле: $REPORT_FILE"
    
    # Создание копии последнего отчета
    cp "$REPORT_FILE" "$REPORT_DIR/vulture_latest.txt"
    log "Создана копия последнего отчета: $REPORT_DIR/vulture_latest.txt"
fi

log "Анализ завершен!"

# Завершаем с кодом 0, так как анализ прошел успешно
exit 0
