import whisper
import torch
import os

def cyrillic_to_latin(text):
    map = {
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
        result += map.get(char, char)
    
    return result

def transcribe_whisper(input_path, output_dir, model, saved_files):

    transcribed_text = ""
    file_name = input_path.rpartition('\\')[2].split(".")[0]

    if file_name in saved_files: 
        msg = file_name + " is skipped because it is already saved"
        print(msg)
        return
    else:
        model = whisper.load_model(model, device=device)
        result = model.transcribe(input_path, language="sr")
        transcribed_text = result["text"]
    
    with open(output_dir + file_name + ".txt", "w", encoding="utf-8") as file:
        file.write(transcribed_text)
    
    print(transcribed_text)

    return transcribed_text

model = "large"
input_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\"
output_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\whisper_large\\"

single_file = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\s1ep1-Rakija.wav"

saved_file_names = ""
for saved_file in os.listdir(output_path):
    saved_file_names += os.fsdecode(saved_file)

device = "cpu"
if model == "large" and torch.cuda.is_available():
    device = "cuda"

if device == "cuda" and torch.cuda.is_available():
    print(f"Using GPU: {torch.cuda.get_device_name(0)}")
else:
    print("Using CPU for processing")


for file in os.listdir(input_path):
    filename = os.fsdecode(file)
    if filename.endswith(".wav"):
        name = os.path.join(input_path, filename)
        transcribe_whisper(name, output_path, model, saved_file_names)
