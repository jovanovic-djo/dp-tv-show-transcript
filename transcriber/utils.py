import whisper
import torch
import os


torch.cuda.is_available()

def transcribe_whisper(input, output_path, model):
    model = whisper.load_model(model)
    result = model.transcribe(input, language="sr", fp16=False, verbose=True, patience=2, beam_size=5)
    
    file_name = input.rpartition('\\')[2].split(".")[0]
    print(file_name)

    file_name += ".txt"
    output_path += file_name
    print(output_path)


    print(result)

    return result


whisper_model = "large-v3"
input_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\"
output_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\whisper_large-v3\\"
single_file = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\s1ep1-Rakija.wav"
    
# for file in os.listdir(input_path):
#     filename = os.fsdecode(file)
#     if filename.endswith(".wav"): 
#         print(filename)
#         continue
#     else:
#         continue

k = transcribe_whisper(single_file, output_path, whisper_model)