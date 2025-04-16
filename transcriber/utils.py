import whisper

def transcribe(file):
    model = whisper.load_model("large-v3")
    result = model.transcribe(file, fp16=False)
    output = file.split(".")

    text_file = open(output, "w")
    text_file.write(result["text"])
    text_file.close()

file = "..\\data\\samples\\audio\\s1ep1-Rakija.webm"
transcribe(file)