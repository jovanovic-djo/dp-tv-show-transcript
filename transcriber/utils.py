import whisper
import torch
import os





def transcribe_whisper(input_path, output_path, input_model):
    model = whisper.load_model(input_model)
    audio = whisper.load_audio(input_path)
    result = model.transcribe(audio, language="sr", fp16=True, verbose=True, patience=2, beam_size=5)
    
    file_name = input_path.rpartition('\\')[2].split(".")[0]
    print(file_name)

    file_name += ".txt"
    output_path += file_name

    text_file = open(output_path, "w")

    text_file.write(result["text"])

    text_file.close()


whisper_model = "large-v3"
input_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\"
output_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\whisper_large-v3\\"
    
# for file in os.listdir(input_path):
#     filename = os.fsdecode(file)
#     if filename.endswith(".wav"): 
#         print(filename)
#         continue
#     else:
#         continue

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:300"

single_file = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\s1ep1-Rakija.wav"

torch.cuda.empty_cache()

import gc
gc.collect()


device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = whisper.load_model('large').to(device)

result = model.transcribe(single_file, )
print(result["text"])


#k = transcribe_whisper(single_file, output_path, whisper_model)