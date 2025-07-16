#!/usr/bin/env python3
"""
Script di avvio per l'interfaccia grafica di Recording to Tasks
"""

import sys
import subprocess
import os
from pathlib import Path

def check_and_install_dependencies():
    """Controlla e installa le dipendenze necessarie"""
    print("🔍 Controllo dipendenze...")
    
    # Controlla se siamo in un virtual environment
    if not (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)):
        print("⚠️  Non sei in un virtual environment!")
        print("💡 Consiglio: attiva il virtual environment con:")
        print("   source venv/bin/activate")
        print()
        
    # Controlla dipendenze GUI
    missing_deps = []
    
    try:
        import tkinter
    except ImportError:
        missing_deps.append("tkinter (dovrebbe essere incluso in Python)")
        
    try:
        import openai
    except ImportError:
        missing_deps.append("openai")
        
    try:
        from dotenv import load_dotenv
    except ImportError:
        missing_deps.append("python-dotenv")
        
    try:
        from tkinterdnd2 import TkinterDnD
        print("✅ tkinterdnd2 disponibile - Drag & Drop attivo")
    except ImportError:
        print("⚠️  tkinterdnd2 non installato - Drag & Drop non disponibile")
        missing_deps.append("tkinterdnd2")
        
    try:
        from PIL import Image
        print("✅ Pillow disponibile")
    except ImportError:
        print("⚠️  Pillow non installato")
        missing_deps.append("Pillow")
    
    if missing_deps:
        print(f"❌ Dipendenze mancanti: {', '.join(missing_deps)}")
        print("🔧 Installazione automatica...")
        
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ Dipendenze installate con successo!")
        except subprocess.CalledProcessError:
            print("❌ Errore nell'installazione delle dipendenze")
            print("💡 Prova manualmente: pip install -r requirements.txt")
            return False
    else:
        print("✅ Tutte le dipendenze sono installate")
    
    return True

def check_api_key():
    """Controlla se la API key è configurata"""
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
            if "OPENAI_API_KEY=" in content and "your_openai_api_key_here" not in content:
                return True
    
    print("⚠️  API Key OpenAI non configurata")
    print("💡 Puoi configurarla tramite l'interfaccia grafica")
    print("   oppure modifica il file .env")
    return False

def main():
    """Funzione principale di avvio"""
    print("🚀 Recording to Tasks - Avvio GUI")
    print("=" * 50)
    
    # Controlla dipendenze
    if not check_and_install_dependencies():
        sys.exit(1)
    
    # Controlla API key
    check_api_key()
    
    # Avvia GUI
    print("\n🎬 Avvio interfaccia grafica...")
    try:
        from gui import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"❌ Errore importazione GUI: {e}")
        print("💡 Assicurati che gui.py sia presente nella directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Errore durante l'avvio: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 