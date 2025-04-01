import os
import subprocess
import time
from pytube import YouTube
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_episode_audio(youtube_url, output_dir, max_retries=3):
    """
    Download a YouTube video as MP3 audio.
    
    Args:
        youtube_url (str): URL of the YouTube video
        output_dir (str): Directory to save the MP3 file
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        str: Path to the downloaded MP3 file or None if download failed
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Second approach: Try with youtube-dl or yt-dlp (if installed)
    try:
        # Try to extract a valid filename from the URL
        video_id = youtube_url.split("v=")[-1].split("&")[0]
        safe_filename = f"video_{video_id}"
        mp3_file = os.path.join(output_dir, f"{safe_filename}.mp3")
        
        logger.info(f"Trying youtube-dl/yt-dlp approach for {youtube_url}")
        
        # Try yt-dlp first (newer fork with better support)
        try:
            subprocess.run(
                ['yt-dlp', '-x', '--audio-format', 'mp3', 
                 '--audio-quality', '0', '-o', f"{output_dir}/{safe_filename}.%(ext)s", 
                 youtube_url],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Successfully downloaded with yt-dlp: {mp3_file}")
            return mp3_file
        except FileNotFoundError:
            logger.info("yt-dlp not found, trying youtube-dl...")
        except subprocess.CalledProcessError as e:
            logger.error(f"yt-dlp download failed: {e}")
        
        # Fall back to youtube-dl
        try:
            subprocess.run(
                ['youtube-dl', '-x', '--audio-format', 'mp3', 
                 '--audio-quality', '0', '-o', f"{output_dir}/{safe_filename}.%(ext)s", 
                 youtube_url],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Successfully downloaded with youtube-dl: {mp3_file}")
            return mp3_file
        except FileNotFoundError:
            logger.warning("youtube-dl not found. Please install yt-dlp or youtube-dl.")
        except subprocess.CalledProcessError as e:
            logger.error(f"youtube-dl download failed: {e}")
        
    except Exception as e:
        logger.error(f"All download approaches failed for {youtube_url}: {str(e)}")
    
    logger.error(f"Failed to download audio from {youtube_url} after multiple attempts")
    return None


# Remove the test code from the module level
if __name__ == "__main__":
    # This only runs when the file is executed directly, not when imported
    test_link = "https://www.youtube.com/watch?v=McwPB-eQ2BY"
    output_dir = "downloaded_audio"
    audio = download_episode_audio(test_link, output_dir)
    if audio:
        print(f"Test successful: {audio}")
    else:
        print("Test failed!")