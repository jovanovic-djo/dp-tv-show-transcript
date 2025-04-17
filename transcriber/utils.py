import whisper
import torch

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

input = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\s1ep1-Rakija.webm"
output_path = "..\\data\\samples\\whisper_large-v3\\"
transcribe(input, output_path)