import whisper
import torch
import os


torch.cuda.is_available()

def transcribe(input, output_path):
    model = whisper.load_model("large-v3")
    result = model.transcribe(input, fp16=False)
    
    file_name = input.rpartition('\\')[2].split(".")[0]
    print(file_name)

    file_name += ".txt"
    output_path += file_name
    print(output_path)

    text_file = open(output_path, "w")
    text_file.write(result["text"])
    text_file.close()



input_path = "..\\dp-tv-show-transcript\\data\\samples\\audio\\"
output_path = "..\\data\\samples\\whisper_large-v3\\"
    
for file in os.listdir(input_path):
    filename = os.fsdecode(file)
    if filename.endswith(".wav"): 
        print(filename)
        continue
    else:
        continue

# transcribe(input_path, output_path)