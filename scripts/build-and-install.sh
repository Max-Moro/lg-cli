#!/bin/bash
# build-and-install.sh - Автоматическая сборка wheel и установка через pipx
set -e

cd "$(dirname "$0")/.."  # переходим в корень проекта cli/

echo "🧹 Cleaning stale build artifacts..."
# Удаляем build/ и *.egg-info для чистой сборки
rm -rf build/ *.egg-info

echo "🔨 Building wheel..."
py -3 -m build --wheel

echo "📦 Finding latest wheel..."
WHEEL=$(ls -1 dist/listing_generator-*.whl | tail -n 1)
if [ -z "$WHEEL" ]; then
    echo "❌ ERROR: No wheel found in dist/"
    exit 1
fi
echo "Found: $WHEEL"

echo "🚀 Installing via pipx..."
py -3 -m pipx install --force "$WHEEL"

echo "✅ Testing installation..."
if listing-generator --version; then
    echo "🎉 Success! listing-generator is ready to use."
else
    echo "⚠️  Installation completed, but 'listing-generator' command not found in PATH."
    echo "   You may need to run: py -3 -m pipx ensurepath"
    echo "   Or restart your terminal/VS Code."
fi

echo ""
echo "💡 To configure VS Code extension, use these settings:"
echo '   "lg.install.strategy": "system",'
echo '   "lg.cli.path": "",'
echo '   "lg.python.interpreter": ""'
echo ""
echo "🔄 Next time: just run './scripts/build-and-install.sh' to update"