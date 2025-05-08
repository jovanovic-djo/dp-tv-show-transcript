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




def transcribe_speech_recognition(audio_file_path, output_file_path=None):
    """
    Transcribes a WAV audio file in Serbian language to text.
    
    Args:
        audio_file_path (str): Path to the WAV audio file
        output_file_path (str, optional): Path to save the transcription. If None, returns the text.
    
    Returns:
        str: Transcribed text if output_file_path is None, otherwise None
    """
    # Validate the audio file exists
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
    
    # Validate it's a WAV file
    if not audio_file_path.lower().endswith('.wav'):
        raise ValueError("Only WAV files are supported")
    
    # Initialize recognizer
    recognizer = sr.Recognizer()
    
    # Load the audio file
    with sr.AudioFile(audio_file_path) as source:
        print(f"Processing audio file: {audio_file_path}")
        # Record the audio data
        audio_data = recognizer.record(source)
    
    try:
        # Recognize speech using Google Speech Recognition with Serbian language
        text = recognizer.recognize_google(audio_data, language="sr-RS")
        print("Transcription successful")
        
        # Save to file if output path is provided
        if output_file_path:
            with open(output_file_path, 'w', encoding='utf-8') as text_file:
                text_file.write(text)
            print(f"Transcription saved to: {output_file_path}")
            return None
        else:
            return text
            
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand the audio")
        return "" if not output_file_path else None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return "" if not output_file_path else None


whisper_model = "large-v3"
input_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\"
output_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\whisper_large-v3\\"

single_file = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio\\s1ep1-Rakija.wav"
    
transcribe_speech_recognition(single_file, output_path)