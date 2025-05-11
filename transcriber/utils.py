import whisper
import speech_recognition as sr
import torch
import os



def transcribe_whisper(input_path, output_path, input_model):

    result = whisper.transcribe(input_path, input_model)
    
    file_name = input_path.rpartition('\\')[2].split(".")[0]
    print(file_name)

    file_name += ".txt"
    output_path += file_name

    text_file = open(output_path, "w")

    text_file.write(result["text"])

    text_file.close()



def transcribe_speech_recognition(input_wav_file, output_txt_file=None, use_whisper=True):
    if not os.path.exists(input_wav_file):
        raise FileNotFoundError(f"Input file {input_wav_file} not found")
    
    if output_txt_file is None:
        base_name = os.path.splitext(input_wav_file)[0]
        output_txt_file = f"{base_name}.txt"
    
    transcribed_text = ""
    
    if use_whisper:
        try:
            model = whisper.load_model("base")
            
            result = model.transcribe(input_wav_file, language="sr")
            transcribed_text = result["text"]
            
        except Exception as e:
            print(f"Error using Whisper: {e}")
            print("Falling back to Google Speech Recognition")
            use_whisper = False
    
    if not use_whisper:
        recognizer = sr.Recognizer()
        
        with sr.AudioFile(input_wav_file) as source:
            audio_data = recognizer.record(source)
            
            try:
                transcribed_text = recognizer.recognize_google(audio_data, language="sr-RS")
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand the audio")
                transcribed_text = "ERROR: Could not transcribe audio"
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")
                transcribed_text = f"ERROR: Speech recognition service error: {e}"

    with open(output_txt_file, "w", encoding="utf-8") as file:
        file.write(transcribed_text)
    
    print(f"Transcription saved to {output_txt_file}")
    return transcribed_text


whisper_model = "large-v3"
input_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\"
output_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\whisper_large-v3\\"

single_file = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\s1ep1-Rakija.wav"

text = transcribe_speech_recognition(single_file)
print(text)