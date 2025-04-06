import os
import subprocess
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from pydub import AudioSegment
import numpy as np

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
    print(f"Loading Whisper {model_size} model on {device}...")
    model_name = f"openai/whisper-{model_size}"
    
    processor = WhisperProcessor.from_pretrained(model_name)
    model = WhisperForConditionalGeneration.from_pretrained(model_name).to(device)
    
    return model, processor, device

def chunk_audio(audio_path, chunk_size_ms=30000):
    audio = AudioSegment.from_file(audio_path)
    duration_ms = len(audio)
    chunks = []
    
    for start_ms in range(0, duration_ms, chunk_size_ms):
        end_ms = min(start_ms + chunk_size_ms, duration_ms)
        chunk = audio[start_ms:end_ms]
        # Convert to numpy array
        samples = np.array(chunk.get_array_of_samples()).astype(np.float32)
        if chunk.channels > 1:
            samples = samples.reshape((-1, chunk.channels)).mean(axis=1)
        samples = samples / 32768.0  # Normalize to [-1, 1]
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
        )
    
    transcription = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return transcription

def transcribe_audio_file(audio_path, model, processor, device, language="sr"):
    print(f"Transcribing {audio_path}...")
    chunks = chunk_audio(audio_path)
    
    full_transcription = ""
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}")
        chunk_transcription = transcribe_audio_chunk(chunk, model, processor, device, language)
        full_transcription += chunk_transcription + " "
    
    return full_transcription.strip()

def process_all_webm_files(directory, output_directory=None, language="sr"):
    if output_directory is None:
        output_directory = directory
    
    os.makedirs(output_directory, exist_ok=True)
    
    model, processor, device = load_whisper_model()
    
    results = {}
    
    for file in os.listdir(directory):
        if file.endswith(".webm"):
            webm_path = os.path.join(directory, file)
            base_name = os.path.splitext(file)[0]
            
            audio_path = extract_audio_from_webm(webm_path)
            
            if audio_path:
                transcription = transcribe_audio_file(audio_path, model, processor, device, language)
                
                txt_path = os.path.join(output_directory, f"{base_name}_transcript.txt")
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(transcription)
                
                results[file] = transcription
                print(f"Saved transcription to {txt_path}")
    
    return results

if __name__ == "__main__":
    input_dir = "..\\downloaded_audio"
    output_dir = "..\\downloaded_audio\\transcripted"
    language = "sr"
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Processing .webm files from: {input_dir}")
    print(f"Saving transcriptions to: {output_dir}")
    
    results = process_all_webm_files(input_dir, output_dir, language)
    
    print(f"\nProcessed {len(results)} files successfully.")
    if results:
        print("\nFiles processed:")
        for file in results:
            print(f"- {file}")