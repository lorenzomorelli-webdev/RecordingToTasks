#!/bin/bash

# Recording to Tasks - Setup Script
# Questo script automatizza l'installazione e la configurazione del progetto

set -e  # Exit on any error

echo "🚀 Recording to Tasks - Setup Script"
echo "====================================="

# Check if we're on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "ℹ️  Sistema operativo rilevato: macOS"
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew non trovato. Installando Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo "✅ Homebrew già installato"
    fi
    
    # Install ffmpeg
    if ! command -v ffmpeg &> /dev/null; then
        echo "📦 Installando ffmpeg..."
        brew install ffmpeg
    else
        echo "✅ ffmpeg già installato"
    fi
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "ℹ️  Sistema operativo rilevato: Linux"
    
    # Check if apt is available (Ubuntu/Debian)
    if command -v apt &> /dev/null; then
        echo "📦 Aggiornando i pacchetti..."
        sudo apt update
        
        if ! command -v ffmpeg &> /dev/null; then
            echo "📦 Installando ffmpeg..."
            sudo apt install -y ffmpeg
        else
            echo "✅ ffmpeg già installato"
        fi
    else
        echo "⚠️  Sistema Linux non supportato automaticamente. Installa manualmente ffmpeg."
    fi
else
    echo "⚠️  Sistema operativo non riconosciuto. Installa manualmente ffmpeg."
fi

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 non trovato. Installalo manualmente."
    exit 1
fi

python_version=$(python3 --version | cut -d' ' -f2)
echo "✅ Python $python_version trovato"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creando ambiente virtuale..."
    python3 -m venv venv
else
    echo "✅ Ambiente virtuale già esistente"
fi

# Activate virtual environment
echo "🔄 Attivando ambiente virtuale..."
source venv/bin/activate

# Install Python dependencies
echo "📦 Installando dipendenze Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creando file .env..."
    cp env.example .env
    echo ""
    echo "⚠️  IMPORTANTE: Modifica il file .env con la tua chiave API di OpenAI!"
    echo "   Apri il file .env e sostituisci 'your_openai_api_key_here' con la tua chiave."
    echo ""
else
    echo "✅ File .env già esistente"
fi

# Create output directories
mkdir -p temp output

echo ""
echo "🎉 Setup completato con successo!"
echo ""
echo "📋 Prossimi passi:"
echo "1. Modifica il file .env con la tua chiave API di OpenAI"
echo "2. Attiva l'ambiente virtuale: source venv/bin/activate"
echo "3. Testa lo script: python main.py --help"
echo "4. Elabora un file: python main.py your_recording.mp4"
echo ""
echo "📚 Per maggiori informazioni, consulta il README.md" 