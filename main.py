#!/usr/bin/env python3
"""
Recording to Tasks - Trasforma registrazioni audio/video in trascrizioni e to-do list

Utilizza OpenAI Whisper per la trascrizione e GPT per l'analisi e generazione di task.
"""

import os
import sys
import argparse
import subprocess
import time
import math
import concurrent.futures
import re
from pathlib import Path
from typing import List, Tuple, Optional

# Third-party imports
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-3.5-turbo")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
MAX_PARALLEL_TASKS = int(os.getenv("MAX_PARALLEL_TASKS", "3"))
SIZE_LIMIT_MB = int(os.getenv("SIZE_LIMIT_MB", "20"))

# Derived constants
SIZE_LIMIT = SIZE_LIMIT_MB * 1024 * 1024  # Convert to bytes
TEMP_DIR = "temp"
OUTPUT_DIR = "output"

# Supported file formats
AUDIO_FORMATS = {'.wav', '.mp3', '.m4a', '.flac', '.aac', '.ogg', '.wma'}
VIDEO_FORMATS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
SUPPORTED_FORMATS = AUDIO_FORMATS | VIDEO_FORMATS

# Initialize OpenAI client
if not OPENAI_API_KEY:
    print("❌ Error: OPENAI_API_KEY not found in environment variables.")
    print("Please create a .env file with your OpenAI API key.")
    sys.exit(1)

client = OpenAI(
    api_key=OPENAI_API_KEY,
    organization=OPENAI_ORG_ID if OPENAI_ORG_ID else None
)

# Create necessary directories
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def log_info(message: str):
    """Log info message with timestamp."""
    print(f"ℹ️  {message}")


def log_success(message: str):
    """Log success message."""
    print(f"✅ {message}")


def log_warning(message: str):
    """Log warning message."""
    print(f"⚠️  {message}")


def log_error(message: str):
    """Log error message."""
    print(f"❌ {message}")


def log_section(message: str):
    """Log section header."""
    print(f"\n🔄 {message}")
    print("=" * (len(message) + 3))


def clean_filename(filepath: str) -> str:
    """Clean filename for safe file operations."""
    filename = Path(filepath).stem
    # Remove special characters and spaces
    clean_name = re.sub(r'[^\w\-_]', '_', filename)
    # Remove consecutive underscores
    clean_name = re.sub(r'_+', '_', clean_name)
    # Remove leading/trailing underscores
    clean_name = clean_name.strip('_')
    return clean_name


def check_dependencies():
    """Check if required external dependencies are installed."""
    try:
        subprocess.run(["ffmpeg", "-version"], 
                      capture_output=True, check=True)
        log_success("ffmpeg is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        log_error("ffmpeg is not installed or not in PATH")
        log_info("Please install ffmpeg:")
        log_info("  macOS: brew install ffmpeg")
        log_info("  Ubuntu: sudo apt install ffmpeg")
        log_info("  Windows: Download from https://ffmpeg.org/download.html")
        sys.exit(1)


def extract_audio_from_video(video_path: str) -> str:
    """Extract audio from video file."""
    clean_name = clean_filename(video_path)
    audio_path = f"{TEMP_DIR}/{clean_name}_extracted.wav"
    
    log_info(f"Extracting audio: {video_path} → {audio_path}")
    try:
        subprocess.run([
            "ffmpeg", "-i", video_path, 
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # Audio codec
            "-ar", "44100",  # Sample rate
            "-ac", "2",  # Stereo
            audio_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log_success("Audio extraction successful!")
        return audio_path
    except subprocess.CalledProcessError as e:
        log_error(f"Error extracting audio from {video_path}: {e}")
        return None


def convert_to_wav(audio_path: str) -> str:
    """Convert audio file to WAV format."""
    # If already extracted, return as-is
    if audio_path.endswith("_extracted.wav"):
        return audio_path
        
    clean_name = clean_filename(audio_path)
    wav_path = f"{TEMP_DIR}/{clean_name}.wav"
    
    log_info(f"Converting: {audio_path} → {wav_path}")
    try:
        subprocess.run([
            "ffmpeg", "-i", audio_path, 
            "-ar", "44100", wav_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log_success("Conversion successful!")
        return wav_path
    except subprocess.CalledProcessError as e:
        log_error(f"Error converting {audio_path}: {e}")
        return None


def get_audio_duration(wav_path: str) -> float:
    """Get the duration of an audio file."""
    duration_cmd = [
        "ffprobe", "-i", wav_path, 
        "-show_entries", "format=duration", 
        "-v", "quiet", "-of", "csv=p=0"
    ]
    duration_output = subprocess.run(duration_cmd, capture_output=True, text=True)
    
    try:
        duration = float(duration_output.stdout.strip())
        log_info(f"Audio duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
        return duration
    except ValueError:
        log_error(f"Could not determine duration of {wav_path}")
        return None


def create_chunks(wav_path: str, duration: float) -> List[Tuple[float, float, str]]:
    """Split audio file into chunks if needed."""
    file_size = os.path.getsize(wav_path)
    clean_name = clean_filename(wav_path)
    
    # If file is already small enough, no need to chunk
    if file_size <= SIZE_LIMIT:
        log_info(f"File size ({file_size/1024/1024:.2f}MB) within limit. No need to chunk.")
        return [(0, duration, wav_path)]
    
    # Calculate number of chunks needed
    num_chunks = math.ceil(file_size / (SIZE_LIMIT * 0.9))  # 10% buffer
    chunk_duration = duration / num_chunks
    
    # Create chunks
    log_info(f"File size ({file_size/1024/1024:.2f}MB) exceeds limit. Splitting into {num_chunks} chunks.")
    chunks = []
    
    for i in range(num_chunks):
        start_time = i * chunk_duration
        end_time = min((i + 1) * chunk_duration, duration)
        chunk_path = f"{TEMP_DIR}/{clean_name}_chunk{i+1}.wav"
        
        # Use ffmpeg to extract the chunk
        subprocess.run([
            "ffmpeg", "-i", wav_path, 
            "-ss", str(start_time), 
            "-to", str(end_time),
            "-c", "copy", chunk_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        chunks.append((start_time, end_time, chunk_path))
        log_success(f"Created chunk {i+1}/{num_chunks}: {start_time:.2f}s to {end_time:.2f}s")
    
    return chunks


def transcribe_chunk(chunk_data: Tuple[float, float, str]) -> Tuple[str, str]:
    """Transcribe audio chunk using OpenAI API with retry logic."""
    start_time, end_time, chunk_path = chunk_data
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            with open(chunk_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model=WHISPER_MODEL,
                    file=audio_file
                )
            
            # Add timestamp prefix to the transcription
            timestamp = f"[{int(start_time//3600):02d}:{int((start_time%3600)//60):02d}:{int(start_time%60):02d}]"
            return timestamp, f"{timestamp} {transcription.text}"
        
        except Exception as e:
            retries += 1
            error_message = str(e)
            log_warning(f"Error transcribing chunk {chunk_path} (attempt {retries}/{MAX_RETRIES}): {error_message}")
            
            # Progressively longer wait between retries
            wait_time = 2 ** retries  # Exponential backoff
            if wait_time > 60:
                wait_time = 60  # Cap at 60 seconds
            
            log_info(f"Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            
            # If this was the last retry, return an error message
            if retries >= MAX_RETRIES:
                log_error(f"Failed to transcribe chunk {chunk_path} after {MAX_RETRIES} attempts: {error_message}")
                timestamp = f"[{int(start_time//3600):02d}:{int((start_time%3600)//60):02d}:{int(start_time%60):02d}]"
                return timestamp, f"{timestamp} [ERROR] Failed to transcribe after {MAX_RETRIES} attempts: {error_message}"


def generate_summary_and_tasks(transcription_text: str, original_filename: str) -> str:
    """Generate summary and tasks from transcription using GPT."""
    log_section("Generating summary and tasks")
    
    prompt = f"""
Analizza questa trascrizione di una riunione/call e genera un documento strutturato con:

1. **RIASSUNTO ESECUTIVO** (2-3 frasi)
2. **PARTECIPANTI** (se identificabili)
3. **PUNTI CHIAVE DISCUSSI** (elenco puntato)
4. **DECISIONI PRESE** (elenco con decisione e contesto)
5. **ACTION ITEMS / TO-DO LIST** (formato: "- [ ] Azione da fare (Responsabile, Scadenza se menzionata)")
6. **PROSSIMI PASSI** (cosa succede dopo)
7. **NOTE AGGIUNTIVE** (informazioni importanti non categorizzate sopra)

Usa un formato Markdown pulito e professionale. Se non riesci a identificare alcune sezioni, scrivi "Non specificato" o "Da definire".

TRASCRIZIONE:
{transcription_text}
"""
    
    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[
                    {"role": "system", "content": "Sei un assistente esperto nell'analisi di riunioni e nella creazione di documenti strutturati. Rispondi sempre in italiano con un formato professionale e chiaro."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            log_success("Summary and tasks generated successfully!")
            return summary
            
        except Exception as e:
            retries += 1
            error_message = str(e)
            log_warning(f"Error generating summary (attempt {retries}/{MAX_RETRIES}): {error_message}")
            
            if retries < MAX_RETRIES:
                wait_time = 2 ** retries
                log_info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                log_error(f"Failed to generate summary after {MAX_RETRIES} attempts")
                return f"# Errore nella generazione del riassunto\n\nNon è stato possibile generare il riassunto per il file {original_filename}.\nErrore: {error_message}\n\n## Trascrizione originale\n\n{transcription_text}"


def process_file(file_path: str) -> bool:
    """Process a single audio/video file."""
    log_section(f"Processing {os.path.basename(file_path)}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        log_error(f"File not found: {file_path}")
        return False
    
    # Check file format
    file_ext = Path(file_path).suffix.lower()
    if file_ext not in SUPPORTED_FORMATS:
        log_error(f"Unsupported file format: {file_ext}")
        log_info(f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}")
        return False
    
    # Extract audio from video if needed
    if file_ext in VIDEO_FORMATS:
        audio_path = extract_audio_from_video(file_path)
        if not audio_path:
            return False
    else:
        audio_path = file_path
    
    # Convert audio to WAV
    wav_path = convert_to_wav(audio_path)
    if not wav_path:
        return False
    
    # Get audio duration
    duration = get_audio_duration(wav_path)
    if not duration:
        return False
    
    # Create chunks if needed
    chunks = create_chunks(wav_path, duration)
    
    # Transcribe each chunk in parallel
    log_section(f"Transcribing {len(chunks)} chunks in parallel (max {MAX_PARALLEL_TASKS} workers)")
    all_transcriptions = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL_TASKS) as executor:
        # Submit all transcription tasks
        future_to_chunk = {executor.submit(transcribe_chunk, chunk): idx for idx, chunk in enumerate(chunks)}
        
        # Process as they complete
        completed = 0
        for future in concurrent.futures.as_completed(future_to_chunk):
            chunk_idx = future_to_chunk[future]
            try:
                timestamp, transcription = future.result()
                all_transcriptions.append((timestamp, transcription))
                completed += 1
                log_success(f"Completed transcription {completed}/{len(chunks)} ({timestamp})")
            except Exception as e:
                log_error(f"Error in chunk {chunk_idx+1}: {str(e)}")
                
    # Sort transcriptions by timestamp
    all_transcriptions.sort()
    sorted_transcriptions = [t[1] for t in all_transcriptions]
    full_transcription = "\n\n".join(sorted_transcriptions)
    
    # Create output filenames
    clean_name = clean_filename(file_path)
    transcription_filename = f"{OUTPUT_DIR}/{clean_name}_transcription.txt"
    tasks_filename = f"{OUTPUT_DIR}/{clean_name}_tasks.md"
    
    # Save transcription
    with open(transcription_filename, "w", encoding="utf-8") as f:
        f.write(f"# Trascrizione di {os.path.basename(file_path)}\n\n")
        f.write(f"**File originale:** {file_path}\n")
        f.write(f"**Durata:** {duration:.2f} secondi ({duration/60:.1f} minuti)\n")
        f.write(f"**Elaborato il:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        f.write(full_transcription)
    
    log_success(f"Transcription saved to: {transcription_filename}")
    
    # Generate and save summary/tasks
    summary = generate_summary_and_tasks(full_transcription, os.path.basename(file_path))
    with open(tasks_filename, "w", encoding="utf-8") as f:
        f.write(f"# Analisi e Task - {os.path.basename(file_path)}\n\n")
        f.write(f"**File originale:** {file_path}\n")
        f.write(f"**Durata:** {duration:.2f} secondi ({duration/60:.1f} minuti)\n")
        f.write(f"**Elaborato il:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        f.write(summary)
    
    log_success(f"Tasks and summary saved to: {tasks_filename}")
    
    # Cleanup temporary files
    for _, _, chunk_path in chunks:
        if chunk_path != wav_path:  # Don't delete the main wav file if it's the only chunk
            try:
                os.remove(chunk_path)
            except:
                pass
    
    # Remove temporary wav file if it was created from video
    if file_ext in VIDEO_FORMATS and wav_path.endswith("_extracted.wav"):
        try:
            os.remove(wav_path)
        except:
            pass
    elif wav_path != audio_path:  # Remove converted wav if different from original
        try:
            os.remove(wav_path)
        except:
            pass
    
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Recording to Tasks - Trasforma registrazioni in trascrizioni e to-do list",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python main.py meeting.mp4
  python main.py call.wav
  python main.py file1.mp4 file2.wav file3.m4a
  
Formati supportati:
  Audio: """ + ", ".join(sorted(AUDIO_FORMATS)) + """
  Video: """ + ", ".join(sorted(VIDEO_FORMATS))
    )
    
    parser.add_argument(
        "files", 
        nargs="+", 
        help="Uno o più file audio/video da processare"
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version="Recording to Tasks 1.0.0"
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    check_dependencies()
    
    # Process each file
    successful = 0
    total = len(args.files)
    
    for file_path in args.files:
        if process_file(file_path):
            successful += 1
        print()  # Add spacing between files
    
    # Final summary
    log_section("Processing Complete")
    log_success(f"Successfully processed {successful}/{total} files")
    
    if successful > 0:
        log_info(f"Output files saved in: {OUTPUT_DIR}/")
        log_info("Files generated:")
        log_info("  - *_transcription.txt (trascrizione completa)")
        log_info("  - *_tasks.md (riassunto e to-do list)")
    
    return 0 if successful == total else 1


if __name__ == "__main__":
    sys.exit(main())
