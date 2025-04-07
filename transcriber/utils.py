import os
import subprocess
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from pydub import AudioSegment
import numpy as np
import re

def extract_audio_from_webm(webm_file, output_file=None):
    if output_file is None:
        output_file = os.path.splitext(webm_file)[0] + ".wav"
    
    try:
        command = [
            "ffmpeg", 
            "-i", webm_file, 
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-af", "highpass=f=50,lowpass=f=7500,volume=1.5",
            "-y",
            output_file
        ]
        
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Successfully extracted audio to {output_file}")
        return output_file
    
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        return None

def load_whisper_model(model_size="large-v3", device="cuda" if torch.cuda.is_available() else "cpu"):
    """Load Whisper model with better error handling and logging."""
    print(f"Loading Whisper {model_size} model on {device}...")
    model_name = f"openai/whisper-{model_size}"
    
    processor = WhisperProcessor.from_pretrained(model_name)
    
    try:
        model = WhisperForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            low_cpu_mem_usage=True
        ).to(device)
    except Exception as e:
        print(f"Encountered error during optimized loading: {e}")
        print("Falling back to standard loading method...")
        model = WhisperForConditionalGeneration.from_pretrained(
            model_name,
            low_cpu_mem_usage=False,
            torch_dtype=torch.float32
        ).to(device)
    
    print(f"Successfully loaded {model_size} model")
    return model, processor, device

def normalize_audio(samples):
    max_norm = np.max(np.abs(samples))
    if max_norm > 0:
        samples = samples / max_norm * 0.9
    
    return samples

def chunk_audio(audio_path, chunk_size_ms=20000, overlap_ms=2000):
    audio = AudioSegment.from_file(audio_path)
    duration_ms = len(audio)
    chunks = []
    
    for start_ms in range(0, duration_ms, chunk_size_ms - overlap_ms):
        end_ms = min(start_ms + chunk_size_ms, duration_ms)
        chunk = audio[start_ms:end_ms]
        samples = np.array(chunk.get_array_of_samples()).astype(np.float32)
        if chunk.channels > 1:
            samples = samples.reshape((-1, chunk.channels)).mean(axis=1)
        samples = samples / 32768.0
        
        samples = normalize_audio(samples)
        
        chunks.append(samples)
    
    return chunks

def transcribe_audio_chunk(chunk, model, processor, device, language="sr"):
    input_features = processor(
        chunk, 
        sampling_rate=16000, 
        return_tensors="pt"
    ).input_features.to(device)
    
    with torch.no_grad():
        forced_decoder_ids = processor.get_decoder_prompt_ids(language=language, task="transcribe")
        generated_ids = model.generate(
            input_features, 
            forced_decoder_ids=forced_decoder_ids,
            max_length=448,
            num_beams=5,
            temperature=0.2,
            no_repeat_ngram_size=3,
            length_penalty=1.0
        )
    
    transcription = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return transcription

def cyrillic_to_latin(text):
    cyrillic_to_latin_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'ђ': 'đ', 'е': 'e', 'ж': 'ž',
        'з': 'z', 'и': 'i', 'ј': 'j', 'к': 'k', 'л': 'l', 'љ': 'lj', 'м': 'm', 'н': 'n',
        'њ': 'nj', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'ћ': 'ć', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'č', 'џ': 'dž', 'ш': 'š',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Ђ': 'Đ', 'Е': 'E', 'Ж': 'Ž',
        'З': 'Z', 'И': 'I', 'Ј': 'J', 'К': 'K', 'Л': 'L', 'Љ': 'Lj', 'М': 'M', 'Н': 'N',
        'Њ': 'Nj', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'Ћ': 'Ć', 'У': 'U',
        'Ф': 'F', 'Х': 'H', 'Ц': 'C', 'Ч': 'Č', 'Џ': 'Dž', 'Ш': 'Š'
    }
    
    for cyr, lat in [('Љ', 'Lj'), ('Њ', 'Nj'), ('Џ', 'Dž')]:
        text = text.replace(cyr, lat)
    
    result = ""
    for char in text:
        result += cyrillic_to_latin_map.get(char, char)
    
    return result

def post_process_transcription(text):
    fixes = [
        (r'\bjel\b', 'je l\''),
        (r'\bjel\'', 'je l\''),
        (r'\bnecu\b', 'neću'),
        (r'\bcu\b', 'ću'),
        (r'\bsta\b', 'šta'),
        (r'(\d),(\d)', r'\1.\2'),
        (r'\s+', ' '),
        (r'\.{2,}', '...'),
    ]
    
    for pattern, replacement in fixes:
        text = re.sub(pattern, replacement, text)
    
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    
    text = re.sub(r'(^|[.!?]\s+)([a-zšđčćž])', lambda m: m.group(1) + m.group(2).upper(), text)
    
    return text

def transcribe_audio_file(audio_path, model, processor, device, language="sr", use_latin=True):
    print(f"Transcribing {audio_path}...")
    chunks = chunk_audio(audio_path, chunk_size_ms=20000, overlap_ms=2000)
    
    full_transcription = ""
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}")
        chunk_transcription = transcribe_audio_chunk(chunk, model, processor, device, language)
        
        if i > 0 and len(full_transcription) > 0:

            full_transcription += " " + chunk_transcription
        else:
            full_transcription += chunk_transcription
    
    full_transcription = post_process_transcription(full_transcription)
    
    if use_latin:
        full_transcription = cyrillic_to_latin(full_transcription)
    
    return full_transcription.strip()

def process_all_webm_files(directory, output_directory=None, language="sr", use_latin=True):
    if output_directory is None:
        output_directory = directory
    
    os.makedirs(output_directory, exist_ok=True)
    
    model, processor, device = load_whisper_model(model_size="large-v3")
    
    results = {}
    
    for file in os.listdir(directory):
        if file.endswith(".webm"):
            webm_path = os.path.join(directory, file)
            base_name = os.path.splitext(file)[0]
            
            audio_path = extract_audio_from_webm(webm_path)
            
            if audio_path:
                transcription = transcribe_audio_file(audio_path, model, processor, device, language, use_latin)
                
                txt_path = os.path.join(output_directory, f"{base_name}.txt")
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(transcription)
                
                results[file] = transcription
                print(f"Saved transcription to {txt_path}")
    
    return results

def process_audio_file(audio_path, output_directory=None, language="sr", use_latin=True):
    if output_directory is None:
        output_directory = os.path.dirname(audio_path)
    
    os.makedirs(output_directory, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    
    model, processor, device = load_whisper_model(model_size="large-v3")
    
    transcription = transcribe_audio_file(audio_path, model, processor, device, language, use_latin)
    
    txt_path = os.path.join(output_directory, f"{base_name}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(transcription)
    
    print(f"Saved transcription to {txt_path}")
    return transcription

if __name__ == "__main__":
    input_dir = "..\\dp-tv-show-transcript\\downloaded_audio\\webm"
    output_dir = "..\\dp-tv-show-transcript\\downloaded_audio\\transcripted"
    language = "sr"
    use_latin = True
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Processing .webm files from: {input_dir}")
    print(f"Saving transcriptions to: {output_dir}")
    print(f"Using Latin script: {use_latin}")
    
    try:
        results = process_all_webm_files(input_dir, output_dir, language, use_latin)
        
        print(f"\nProcessed {len(results)} files successfully.")
        if results:
            print("\nFiles processed:")
            for file in results:
                print(f"- {file}")
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()