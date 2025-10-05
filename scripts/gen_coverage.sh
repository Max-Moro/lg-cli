#!/bin/bash

# Скрипт для генерации HTML-отчета тестового покрытия
# Автор: AI Assistant
# Описание: Запускает pytest с coverage и генерирует HTML-отчет в папке htmlcov/

set -e

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
    log "Создайте виртуальное окружение: python -m venv .venv"
    exit 1
fi

# Определение пути к Python в зависимости от ОС
if [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    error "Не удалось найти интерпретатор Python в .venv!"
    exit 1
fi

log "Используется Python: $PYTHON"

# Проверка установки pytest и coverage
if ! $PYTHON -m pytest --version > /dev/null 2>&1; then
    error "pytest не установлен в виртуальном окружении!"
    log "Установите зависимости: $PYTHON -m pip install -e \".[dev]\""
    exit 1
fi

if ! $PYTHON -m pip show coverage > /dev/null 2>&1; then
    warning "coverage не установлен, устанавливаю..."
    $PYTHON -m pip install coverage pytest-cov
fi

log "Удаление старых данных покрытия..."
rm -rf .coverage htmlcov/

log "Запуск тестов с измерением покрытия..."
$PYTHON -m pytest --cov=lg --cov-report=html --cov-report=term tests/

# Проверка успешности выполнения
if [ $? -eq 0 ]; then
    success "Тесты успешно выполнены!"
    
    if [ -d "htmlcov" ]; then
        success "HTML-отчет о покрытии сгенерирован в папке htmlcov/"
        log "Откройте htmlcov/index.html в браузере для просмотра отчета"
    else
        warning "Папка htmlcov не была создана"
    fi
else
    error "При выполнении тестов произошли ошибки"
    exit 1
fi
