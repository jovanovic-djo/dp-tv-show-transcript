import whisper
import speech_recognition as sr
import torch
import os



def transcribe_whisperr(input_path, output_path, input_model):

    result = whisper.transcribe(input_path, input_model)
    
    file_name = input_path.rpartition('\\')[2].split(".")[0]
    print(file_name)

    file_name += ".txt"
    output_path += file_name

    text_file = open(output_path, "w")

    text_file.write(result["text"])

    text_file.close()



def transcribe_whisper(input_path, output_dir):

    transcribed_text = ""
    file_name = input_path.rpartition('\\')[2].split(".")[0]

    model = whisper.load_model("small")
    
    result = model.transcribe(input_path, language="sr")
    transcribed_text = result["text"]

    with open(output_dir + file_name, "w", encoding="utf-8") as file:
        file.write(transcribed_text)
    
    print(f"Transcription saved to {output_dir}")
    return transcribed_text


input_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\"
output_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\whisper_small\\"

single_file = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\s1ep1-Rakija.wav"

text = transcribe_whisper(single_file, output_path)
print(text)