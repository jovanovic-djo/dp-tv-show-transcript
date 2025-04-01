import os
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_episode(youtube_url, output_dir):

    os.makedirs(output_dir, exist_ok=True)

    video_id = youtube_url.split("v=")[-1].split("&")[0]
    safe_filename = f"video_{video_id}"
    output_template = os.path.join(output_dir, f"{safe_filename}.%(ext)s")
    
    logger.info(f"Downloading audio from {youtube_url}")
    
    process = subprocess.run(
        ['yt-dlp', 
            '-f', 'bestaudio',
            '--no-playlist',
            '--progress',
            '-o', output_template,
            youtube_url],
        capture_output=True,
        text=True, 
        check=False 
    )
    
    logger.info(f"yt-dlp stdout: {process.stdout}")
    if process.stderr:
        logger.warning(f"yt-dlp stderr: {process.stderr}")
        
    if process.returncode != 0:
        logger.error(f"yt-dlp failed with exit code {process.returncode}")
        return None
        
    downloaded_files = [f for f in os.listdir(output_dir) if f.startswith(f"video_{video_id}")]
    if not downloaded_files:
        logger.error("Download succeeded but file not found")
        return None
            
    downloaded_file = os.path.join(output_dir, downloaded_files[0])
    logger.info(f"Successfully downloaded file: {downloaded_file}")
    return downloaded_file
                

def convert_to_mp3(input_file, output_dir=None):
    try:
        if not os.path.exists(input_file):
            logger.error(f"Input file does not exist: {input_file}")
            return None
            
        if input_file.lower().endswith('.mp3'):
            logger.info(f"File is already in MP3 format: {input_file}")
            return input_file
            
        if output_dir is None:
            output_dir = os.path.dirname(input_file)
            
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.basename(input_file)
        file_name_without_ext = os.path.splitext(base_name)[0]
        mp3_file = os.path.join(output_dir, f"{file_name_without_ext}.mp3")
        
        logger.info(f"Converting {input_file} to MP3")
        
        process = subprocess.run(
            ['ffmpeg', '-i', input_file, '-codec:a', 'libmp3lame', '-qscale:a', '1', '-y', mp3_file],
            capture_output=True,
            text=True,
            check=False
        )
        
        if process.returncode != 0:
            logger.error(f"FFmpeg conversion failed: {process.stderr}")
            return None
            
        if os.path.exists(mp3_file):
            logger.info(f"Successfully converted to MP3: {mp3_file}")
            
            os.remove(input_file)
            
            return mp3_file
        else:
            logger.error("Conversion seemed to succeed but MP3 file was not found")
            return None
            
    except Exception as e:
        logger.error(f"Error converting to MP3: {str(e)}")
        return None


if __name__ == "__main__":
    test_link = "https://www.youtube.com/watch?v=McwPB-eQ2BY"
    output_dir = "downloaded_audio"
    
    downloaded_file = download_episode(test_link, output_dir)
    if downloaded_file:
        audio = convert_to_mp3(downloaded_file, output_dir)
    else:
        audio = None
    
    if audio:
        logger.info(f"Process successful: {audio}")
    else:
        logger.error("Process failed")