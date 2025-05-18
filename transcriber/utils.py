import whisper
import torch
import os


def transcribe_whisper(input_path, output_dir, model):

    transcribed_text = ""
    file_name = input_path.rpartition('\\')[2].split(".")[0]

    device = "cpu"
    if model == "large" and torch.cuda.is_available():
        device = "cuda"

    if device == "cuda" and torch.cuda.is_available():
        print(f"Using GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("Using CPU for processing")

    for saved_file in os.listdir(output_dir):
        saved_file_name = os.fsdecode(saved_file)

        print("file_name: " + file_name)
        print("saved_file: " + saved_file)
        print("saved_file_name: " + saved_file_name)

        if file_name in saved_file_name: 
            msg = saved_file_name + " is skipped because it is already saved"
            print(msg)
            return
        else:
            model = whisper.load_model(model, device=device)
            result = model.transcribe(input_path, language="sr")
            transcribed_text = result["text"]
            break

    
    with open(output_dir + file_name, "w", encoding="utf-8") as file:
        file.write(transcribed_text)
    
    print(transcribed_text)

    return transcribed_text

model = "base"
input_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\"
output_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\whisper_base\\"

single_file = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\s1ep1-Rakija.wav"


for file in os.listdir(input_path):
    filename = os.fsdecode(file)
    if filename.endswith(".wav"): 
        print(filename)
        name = os.path.join(input_path, filename)
        transcribe_whisper(name, output_path, model)
