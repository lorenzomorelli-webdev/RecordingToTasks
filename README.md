# Recording to Tasks

Un tool Python che trasforma le registrazioni audio/video di meeting in trascrizioni e to-do list strutturate utilizzando le API di OpenAI (Whisper per la trascrizione e GPT per l'analisi).

## 🚀 Funzionalità

- **Trascrizione automatica** di file audio e video usando Whisper
- **Estrazione intelligente** di task, decisioni e action item dal contenuto
- **Gestione file grandi** con chunking automatico
- **Supporto multi-formato** (MP4, MOV, WAV, MP3, M4A, etc.)
- **Elaborazione parallela** per velocizzare la trascrizione
- **Retry automatico** in caso di errori API
- **Timestamp precisi** per ogni sezione

## 🛠️ Setup e Installazione

### Prerequisiti

1. **Python 3.8+** installato sul sistema
2. **ffmpeg** installato:
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt update && sudo apt install ffmpeg
   
   # Windows
   # Scarica da https://ffmpeg.org/download.html
   ```
3. **Account OpenAI** con API key

### Installazione

#### Opzione 1: Setup Automatico (Consigliato)

1. **Clona il repository:**
   ```bash
   git clone <repository-url>
   cd RecordingToTasks
   ```

2. **Esegui lo script di setup:**
   ```bash
   ./setup.sh
   ```
   
   Lo script installerà automaticamente:
   - ffmpeg (se non presente)
   - L'ambiente virtuale Python
   - Tutte le dipendenze necessarie
   - Creerà il file `.env` dal template

3. **Configura la tua API key:**
   
   Modifica il file `.env` inserendo la tua API key di OpenAI:
   ```
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

#### Opzione 2: Setup Manuale

1. **Clona il repository:**
   ```bash
   git clone <repository-url>
   cd RecordingToTasks
   ```

2. **Crea e attiva l'ambiente virtuale:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Su Windows: venv\Scripts\activate
   ```

3. **Installa le dipendenze:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura le variabili d'ambiente:**
   ```bash
   cp env.example .env
   ```
   
   Modifica il file `.env` inserendo la tua API key di OpenAI:
   ```
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

### Verifica dell'installazione

```bash
python main.py --help
```

## 📖 Utilizzo

### 🖥️ Interfaccia Grafica (Consigliata)

Per un'esperienza user-friendly con drag & drop:

```bash
python start_gui.py
```

**Funzionalità GUI:**
- 🎬 **Drag & Drop**: Trascina file audio/video direttamente nell'interfaccia
- 📂 **File Browser**: Selezione file tramite finestra di dialogo
- ⚙️ **Configurazione Modelli**: Scegli tra gpt-4o-mini, gpt-3.5-turbo, gpt-4o
- 💰 **Stima Costi**: Calcolo automatico dei costi prima dell'elaborazione
- 📊 **Monitoraggio**: Progress bar e log in tempo reale
- 🔑 **Gestione API Key**: Configurazione semplificata tramite interfaccia

### 📟 Linea di Comando

```bash
python main.py /path/to/your/recording.mp4
```

### Esempi

```bash
# Trascrivi un file video
python main.py meeting_2024_01_15.mp4

# Trascrivi un file audio
python main.py call_with_client.wav

# Elabora più file
python main.py file1.mp4 file2.wav file3.m4a
```

### Output

Il tool genererà due file nella cartella `output/`:

1. **`filename_transcription.txt`** - Trascrizione completa con timestamp
2. **`filename_tasks.md`** - To-do list strutturata con:
   - Action items e responsabili
   - Decisioni chiave prese
   - Scadenze e date importanti
   - Riassunto della discussione

## ⚙️ Configurazione

### Variabili d'ambiente (file `.env`)

```bash
# API Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_ORG_ID=your_org_id_here  # Opzionale

# Model Selection
WHISPER_MODEL=whisper-1          # Modello per trascrizione
CHAT_MODEL=gpt-3.5-turbo        # Modello per analisi (o gpt-4-turbo)

# Processing Configuration
MAX_RETRIES=3                    # Retry in caso di errore
MAX_PARALLEL_TASKS=3            # Task paralleli per trascrizione
SIZE_LIMIT_MB=20                # Limite dimensione file (MB)
```

### Modelli disponibili

**Per la trascrizione:**
- `whisper-1` - Modello standard, ottimo rapporto qualità/prezzo

**Per l'analisi:**
- `gpt-3.5-turbo` - Veloce ed economico, qualità 7-8/10
- `gpt-4-turbo` - Più preciso ma costoso, qualità 9-10/10

## 💰 Costi Stimati

I costi dipendono dalla lunghezza delle registrazioni:

**Whisper (trascrizione):**
- $0.006 per minuto di audio

**GPT-3.5-turbo (analisi):**
- ~$0.001-0.003 per meeting di 1 ora

**Esempio:** Meeting di 1 ora = ~$0.36 + $0.002 = **~$0.37 totale**

## 🔧 Sviluppo

### Struttura del progetto

```
RecordingToTasks/
├── main.py              # Script principale
├── requirements.txt     # Dipendenze Python
├── .env                 # Configurazione (non committato)
├── env.example          # Template configurazione
├── README.md           # Documentazione
├── .gitignore          # File da ignorare
├── venv/               # Ambiente virtuale
├── temp/               # File temporanei
└── output/             # File di output
```

### Contribuire

1. Fork del repository
2. Crea un branch per la feature: `git checkout -b feature/nome-feature`
3. Commit delle modifiche: `git commit -am 'Aggiunge nuova feature'`
4. Push del branch: `git push origin feature/nome-feature`
5. Apri una Pull Request

## 🐛 Risoluzione problemi

### Errori comuni

**"ffmpeg not found"**
```bash
# Verifica installazione
ffmpeg -version

# Se non installato, segui i prerequisiti
```

**"OpenAI API key not found"**
```bash
# Verifica file .env
cat .env

# Assicurati che la chiave sia corretta
```

**"File troppo grande"**
- Il tool gestisce automaticamente file grandi
- Aumenta `SIZE_LIMIT_MB` in `.env` se necessario

### Debug

Attiva il logging dettagliato modificando il file `main.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📄 Licenza

MIT License - vedi file LICENSE per dettagli

## 🤝 Supporto

Per bug report o feature request, apri una issue su GitHub.

---

**Nota:** Questo tool è ottimizzato per meeting in italiano e inglese. Per altre lingue, potrebbe essere necessario ajustare i prompt di analisi. 