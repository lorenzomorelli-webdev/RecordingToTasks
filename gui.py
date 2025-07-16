#!/usr/bin/env python3
"""
Recording to Tasks - Interfaccia Grafica
Interfaccia user-friendly con drag & drop per la trascrizione e generazione task
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import os
import sys
from pathlib import Path
from typing import List, Optional
import json
import webbrowser

# Tkinter DND support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    print("⚠️  tkinterdnd2 non installato. Drag & drop non disponibile.")

# Import del nostro modulo principale
try:
    from main import (
        validate_api_key, get_file_duration, split_audio, 
        transcribe_audio_chunk, generate_tasks_from_transcription,
        WHISPER_MODEL, CHAT_MODEL, SIZE_LIMIT_MB
    )
except ImportError as e:
    print(f"❌ Errore importazione main.py: {e}")
    sys.exit(1)

class RecordingToTasksGUI:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.setup_variables()
        self.setup_ui()
        self.setup_drag_drop()
        
        # Queue per comunicazione thread
        self.message_queue = queue.Queue()
        self.check_queue()
        
    def setup_window(self):
        """Configura la finestra principale"""
        self.root.title("Recording to Tasks - AI Transcription & Task Generator")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Centra la finestra
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.root.winfo_screenheight() // 2) - (700 // 2)
        self.root.geometry(f"900x700+{x}+{y}")
        
        # Icona e stile
        self.root.configure(bg='#f0f0f0')
        
    def setup_variables(self):
        """Inizializza le variabili"""
        self.current_file = None
        self.processing = False
        self.transcription_result = ""
        self.tasks_result = ""
        
        # Variabili per i modelli
        self.whisper_model = tk.StringVar(value="whisper-1")
        self.chat_model = tk.StringVar(value="gpt-4o-mini")
        self.max_retries = tk.IntVar(value=3)
        
    def setup_ui(self):
        """Crea l'interfaccia utente"""
        # Frame principale
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configura il grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Titolo
        title_label = ttk.Label(main_frame, text="🎙️ Recording to Tasks", 
                               font=("Arial", 18, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Sezione configurazione modelli
        self.setup_model_config(main_frame, row=1)
        
        # Sezione file input
        self.setup_file_input(main_frame, row=2)
        
        # Sezione controlli
        self.setup_controls(main_frame, row=3)
        
        # Progress bar
        self.setup_progress(main_frame, row=4)
        
        # Sezione output
        self.setup_output(main_frame, row=5)
        
        # Status bar
        self.setup_status(main_frame, row=6)
        
    def setup_model_config(self, parent, row):
        """Sezione configurazione modelli"""
        config_frame = ttk.LabelFrame(parent, text="⚙️ Configurazione Modelli", padding="10")
        config_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(3, weight=1)
        
        # Whisper Model
        ttk.Label(config_frame, text="Trascrizione:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        whisper_combo = ttk.Combobox(config_frame, textvariable=self.whisper_model, 
                                   values=["whisper-1"], state="readonly", width=15)
        whisper_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 20))
        
        # Chat Model
        ttk.Label(config_frame, text="Analisi Task:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        chat_combo = ttk.Combobox(config_frame, textvariable=self.chat_model,
                                values=["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o"], 
                                state="readonly", width=15)
        chat_combo.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(0, 20))
        
        # Retry setting
        ttk.Label(config_frame, text="Max Retry:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        retry_spin = ttk.Spinbox(config_frame, from_=1, to=10, textvariable=self.max_retries, width=5)
        retry_spin.grid(row=0, column=5, sticky=tk.W)
        
        # Stima costi
        self.cost_label = ttk.Label(config_frame, text="💰 Costo stimato: $0.00", 
                                   foreground="green")
        self.cost_label.grid(row=1, column=0, columnspan=6, pady=(10, 0))
        
    def setup_file_input(self, parent, row):
        """Sezione input file"""
        file_frame = ttk.LabelFrame(parent, text="📁 Selezione File", padding="15")
        file_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        
        # Drop zone
        self.drop_frame = tk.Frame(file_frame, bg='#e8f4f8', relief='dashed', bd=2, height=120)
        self.drop_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.drop_frame.columnconfigure(0, weight=1)
        self.drop_frame.rowconfigure(0, weight=1)
        
        # Label per drag & drop
        if DND_AVAILABLE:
            drop_text = "🎬 Trascina qui il file audio/video\n\nFormati supportati: MP4, MOV, AVI, WAV, MP3, M4A, FLAC"
        else:
            drop_text = "📁 Usa il pulsante 'Sfoglia' per selezionare il file\n\nFormati supportati: MP4, MOV, AVI, WAV, MP3, M4A, FLAC"
            
        self.drop_label = tk.Label(self.drop_frame, text=drop_text, 
                                  bg='#e8f4f8', fg='#2c3e50', font=("Arial", 11))
        self.drop_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=20, pady=20)
        
        # File info
        self.file_info_label = ttk.Label(file_frame, text="Nessun file selezionato", 
                                        foreground="gray")
        self.file_info_label.grid(row=1, column=0, sticky=tk.W)
        
        # Pulsante sfoglia
        browse_btn = ttk.Button(file_frame, text="📂 Sfoglia File", command=self.browse_file)
        browse_btn.grid(row=2, column=0, pady=(10, 0))
        
    def setup_controls(self, parent, row):
        """Sezione controlli"""
        controls_frame = ttk.Frame(parent)
        controls_frame.grid(row=row, column=0, columnspan=3, pady=(0, 10))
        
        # Pulsante principale
        self.process_btn = ttk.Button(controls_frame, text="🚀 Avvia Trascrizione e Analisi", 
                                     command=self.start_processing, style="Accent.TButton")
        self.process_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Pulsante stop
        self.stop_btn = ttk.Button(controls_frame, text="⏹️ Stop", 
                                  command=self.stop_processing, state="disabled")
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Pulsante clear
        clear_btn = ttk.Button(controls_frame, text="🗑️ Pulisci", command=self.clear_output)
        clear_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Pulsante API key
        api_btn = ttk.Button(controls_frame, text="🔑 Configura API Key", 
                           command=self.configure_api_key)
        api_btn.pack(side=tk.LEFT)
        
    def setup_progress(self, parent, row):
        """Barra di progresso"""
        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.progress_label = ttk.Label(progress_frame, text="Pronto")
        self.progress_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
    def setup_output(self, parent, row):
        """Sezione output"""
        output_frame = ttk.LabelFrame(parent, text="📋 Risultati", padding="10")
        output_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        # Notebook per tabs
        self.notebook = ttk.Notebook(output_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Tab trascrizione
        transcription_frame = ttk.Frame(self.notebook)
        self.notebook.add(transcription_frame, text="📝 Trascrizione")
        
        self.transcription_text = scrolledtext.ScrolledText(transcription_frame, wrap=tk.WORD, 
                                                           height=15, font=("Consolas", 10))
        self.transcription_text.pack(fill=tk.BOTH, expand=True)
        
        # Tab tasks
        tasks_frame = ttk.Frame(self.notebook)
        self.notebook.add(tasks_frame, text="✅ Task e Punti Chiave")
        
        self.tasks_text = scrolledtext.ScrolledText(tasks_frame, wrap=tk.WORD, 
                                                   height=15, font=("Consolas", 10))
        self.tasks_text.pack(fill=tk.BOTH, expand=True)
        
        # Tab log
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="📊 Log")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, 
                                                 height=15, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
    def setup_status(self, parent, row):
        """Status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(status_frame, text="✅ Pronto per l'elaborazione", 
                                     foreground="green")
        self.status_label.pack(side=tk.LEFT)
        
        # Link documentazione
        doc_link = ttk.Label(status_frame, text="📖 Documentazione", 
                           foreground="blue", cursor="hand2")
        doc_link.pack(side=tk.RIGHT)
        doc_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/yourusername/RecordingToTasks"))
        
    def setup_drag_drop(self):
        """Configura drag & drop se disponibile"""
        if DND_AVAILABLE:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)
            
    def on_drop(self, event):
        """Gestisce il drop di file"""
        files = event.data.split()
        if files:
            file_path = files[0].strip('{}')  # Rimuove le parentesi graffe se presenti
            self.select_file(file_path)
            
    def browse_file(self):
        """Apre il file browser"""
        filetypes = [
            ("File Audio/Video", "*.mp4 *.mov *.avi *.mkv *.wav *.mp3 *.m4a *.flac *.aac"),
            ("Video", "*.mp4 *.mov *.avi *.mkv"),
            ("Audio", "*.wav *.mp3 *.m4a *.flac *.aac"),
            ("Tutti i file", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="Seleziona file audio o video",
            filetypes=filetypes
        )
        
        if file_path:
            self.select_file(file_path)
            
    def select_file(self, file_path):
        """Seleziona un file e aggiorna l'interfaccia"""
        try:
            path = Path(file_path)
            if not path.exists():
                messagebox.showerror("Errore", f"File non trovato: {file_path}")
                return
                
            # Verifica estensione
            valid_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.wav', '.mp3', '.m4a', '.flac', '.aac'}
            if path.suffix.lower() not in valid_extensions:
                messagebox.showerror("Errore", f"Formato file non supportato: {path.suffix}")
                return
                
            # Verifica dimensione
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > SIZE_LIMIT_MB:
                messagebox.showerror("Errore", 
                                   f"File troppo grande: {file_size_mb:.1f}MB\n"
                                   f"Limite massimo: {SIZE_LIMIT_MB}MB")
                return
                
            self.current_file = file_path
            
            # Aggiorna interfaccia
            self.drop_label.config(text=f"✅ File selezionato:\n{path.name}")
            self.file_info_label.config(text=f"📁 {path.name} ({file_size_mb:.1f}MB)", 
                                       foreground="black")
            
            # Stima durata e costi
            self.estimate_costs()
            
            # Abilita pulsante process
            self.process_btn.config(state="normal")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nella selezione del file: {str(e)}")
            
    def estimate_costs(self):
        """Stima i costi di elaborazione"""
        if not self.current_file:
            return
            
        try:
            # Ottieni durata
            duration = get_file_duration(self.current_file)
            
            # Costi Whisper
            whisper_cost = (duration / 60) * 0.006  # $0.006 per minuto
            
            # Stima costi chat (approssimativo)
            estimated_tokens = duration * 250  # ~250 token per minuto di trascrizione
            
            if self.chat_model.get() == "gpt-4o-mini":
                # $0.150 input + $0.600 output per 1M token
                chat_cost = (estimated_tokens / 1000000) * 0.150 + (estimated_tokens * 0.2 / 1000000) * 0.600
            elif self.chat_model.get() == "gpt-3.5-turbo":
                # $0.500 input + $1.500 output per 1M token
                chat_cost = (estimated_tokens / 1000000) * 0.500 + (estimated_tokens * 0.2 / 1000000) * 1.500
            else:  # gpt-4o
                # $2.500 input + $10.000 output per 1M token
                chat_cost = (estimated_tokens / 1000000) * 2.500 + (estimated_tokens * 0.2 / 1000000) * 10.000
                
            total_cost = whisper_cost + chat_cost
            
            self.cost_label.config(text=f"💰 Durata: {duration/60:.1f}min | Costo stimato: ${total_cost:.3f}")
            
        except Exception as e:
            self.cost_label.config(text=f"💰 Errore stima costi: {str(e)}")
            
    def configure_api_key(self):
        """Apre dialog per configurare API key"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Configurazione API Key")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centra il dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"400x200+{x}+{y}")
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Inserisci la tua OpenAI API Key:").pack(pady=(0, 10))
        
        api_key_var = tk.StringVar()
        api_entry = ttk.Entry(frame, textvariable=api_key_var, width=50, show="*")
        api_entry.pack(pady=(0, 10))
        api_entry.focus()
        
        def save_api_key():
            key = api_key_var.get().strip()
            if key:
                # Salva nel file .env
                env_path = Path(".env")
                env_content = f"OPENAI_API_KEY={key}\n"
                
                if env_path.exists():
                    # Aggiorna .env esistente
                    with open(env_path, 'r') as f:
                        lines = f.readlines()
                    
                    updated = False
                    for i, line in enumerate(lines):
                        if line.startswith("OPENAI_API_KEY="):
                            lines[i] = env_content
                            updated = True
                            break
                    
                    if not updated:
                        lines.append(env_content)
                        
                    with open(env_path, 'w') as f:
                        f.writelines(lines)
                else:
                    # Crea nuovo .env
                    with open(env_path, 'w') as f:
                        f.write(env_content)
                
                messagebox.showinfo("Successo", "API Key salvata correttamente!")
                dialog.destroy()
            else:
                messagebox.showerror("Errore", "Inserisci una API Key valida")
                
        ttk.Button(frame, text="Salva", command=save_api_key).pack(pady=(0, 5))
        ttk.Button(frame, text="Annulla", command=dialog.destroy).pack()
        
    def start_processing(self):
        """Avvia l'elaborazione in un thread separato"""
        if not self.current_file:
            messagebox.showerror("Errore", "Seleziona prima un file")
            return
            
        # Verifica API key
        if not validate_api_key():
            messagebox.showerror("Errore", 
                               "API Key OpenAI non configurata o non valida.\n"
                               "Usa il pulsante 'Configura API Key' per impostarla.")
            return
            
        self.processing = True
        self.process_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress.start()
        
        # Pulisci output precedente
        self.clear_output()
        
        # Avvia thread di elaborazione
        self.processing_thread = threading.Thread(target=self.process_file)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
    def process_file(self):
        """Elabora il file (eseguito in thread separato)"""
        try:
            self.message_queue.put(("status", "🔄 Avvio elaborazione..."))
            self.message_queue.put(("log", f"📁 File: {self.current_file}\n"))
            
            # 1. Ottieni durata
            duration = get_file_duration(self.current_file)
            self.message_queue.put(("log", f"⏱️ Durata: {duration:.1f} secondi\n"))
            
            # 2. Split audio se necessario
            self.message_queue.put(("status", "✂️ Preparazione audio..."))
            audio_chunks = split_audio(self.current_file)
            self.message_queue.put(("log", f"📦 Creati {len(audio_chunks)} chunk audio\n"))
            
            # 3. Trascrizione
            self.message_queue.put(("status", "🎙️ Trascrizione in corso..."))
            transcription_parts = []
            
            for i, chunk_path in enumerate(audio_chunks):
                if not self.processing:  # Check stop flag
                    break
                    
                self.message_queue.put(("log", f"🎯 Elaborazione chunk {i+1}/{len(audio_chunks)}\n"))
                
                transcript = transcribe_audio_chunk(
                    chunk_path, 
                    self.whisper_model.get(), 
                    self.max_retries.get()
                )
                
                if transcript:
                    transcription_parts.append(transcript)
                    
            # Unisci trascrizioni
            full_transcription = "\n".join(transcription_parts)
            self.message_queue.put(("transcription", full_transcription))
            
            if not self.processing:
                return
                
            # 4. Generazione task
            self.message_queue.put(("status", "🤖 Generazione task..."))
            tasks = generate_tasks_from_transcription(
                full_transcription, 
                self.chat_model.get(), 
                self.max_retries.get()
            )
            
            self.message_queue.put(("tasks", tasks))
            self.message_queue.put(("status", "✅ Elaborazione completata!"))
            self.message_queue.put(("log", "🎉 Processo completato con successo!\n"))
            
        except Exception as e:
            self.message_queue.put(("error", f"Errore durante l'elaborazione: {str(e)}"))
            self.message_queue.put(("log", f"❌ ERRORE: {str(e)}\n"))
        finally:
            self.message_queue.put(("finished", None))
            
    def stop_processing(self):
        """Ferma l'elaborazione"""
        self.processing = False
        self.message_queue.put(("status", "⏹️ Elaborazione interrotta"))
        self.message_queue.put(("log", "⏹️ Elaborazione interrotta dall'utente\n"))
        
    def clear_output(self):
        """Pulisce l'output"""
        self.transcription_text.delete(1.0, tk.END)
        self.tasks_text.delete(1.0, tk.END)
        self.log_text.delete(1.0, tk.END)
        
    def check_queue(self):
        """Controlla la queue dei messaggi dal thread"""
        try:
            while True:
                message_type, data = self.message_queue.get_nowait()
                
                if message_type == "status":
                    self.progress_label.config(text=data)
                    self.status_label.config(text=data)
                elif message_type == "log":
                    self.log_text.insert(tk.END, data)
                    self.log_text.see(tk.END)
                elif message_type == "transcription":
                    self.transcription_text.insert(tk.END, data)
                    self.transcription_result = data
                elif message_type == "tasks":
                    self.tasks_text.insert(tk.END, data)
                    self.tasks_result = data
                elif message_type == "error":
                    messagebox.showerror("Errore", data)
                    self.status_label.config(text="❌ Errore nell'elaborazione", foreground="red")
                elif message_type == "finished":
                    self.processing = False
                    self.process_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    self.progress.stop()
                    
        except queue.Empty:
            pass
            
        # Ricontrolla dopo 100ms
        self.root.after(100, self.check_queue)

def main():
    """Funzione principale"""
    # Verifica dipendenze
    try:
        import openai
        from dotenv import load_dotenv
    except ImportError as e:
        print(f"❌ Dipendenza mancante: {e}")
        print("Esegui: pip install -r requirements.txt")
        sys.exit(1)
    
    # Crea finestra principale
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    # Configura stile
    style = ttk.Style()
    style.theme_use('clam')
    
    # Crea applicazione
    app = RecordingToTasksGUI(root)
    
    # Gestione chiusura
    def on_closing():
        if app.processing:
            if messagebox.askokcancel("Chiusura", "Elaborazione in corso. Vuoi davvero chiudere?"):
                app.processing = False
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Avvia applicazione
    root.mainloop()

if __name__ == "__main__":
    main() 