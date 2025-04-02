import os
import subprocess
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_episode(csv_path):
    try:
        df = pd.read_csv(csv_path)
        not_downloaded = df[df['downloaded'] == False]
        
        if not_downloaded.empty:
            logger.info("All episodes have been downloaded.")
            return None
            
        episode = not_downloaded.iloc[0].to_dict()
        episode_index = not_downloaded.index[0]
        episode['index'] = episode_index
        
        logger.info(f"Found episode to download: Season {episode['season']}, Episode {episode['episode_number']} - {episode['episode_name']}")
        
        return episode
    
    except Exception as e:
        logger.error(f"Error reading CSV file {csv_path}: {str(e)}")
        return None

def update_episode_status(csv_path, episode_index, status_column='downloaded', value=True):
    try:
        df = pd.read_csv(csv_path)
        df.loc[episode_index, status_column] = value
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Updated episode at index {episode_index}, set {status_column} to {value}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating CSV file {csv_path}: {str(e)}")
        return False

def download_episode(youtube_url, output_dir, episode_info=None):
    try:
        os.makedirs(output_dir, exist_ok=True)

        if episode_info:
            season = episode_info['season']
            episode_number = episode_info['episode_number']
            episode_name = episode_info['episode_name'].replace(" ", "_")
            
            safe_filename = f"s{season}ep{episode_number}-{episode_name}"
            safe_filename = "".join([c for c in safe_filename if c.isalpha() or c.isdigit() or c in ' -_']).rstrip()
        else:
            video_id = youtube_url.split("v=")[-1].split("&")[0]
            safe_filename = f"video_{video_id}"
            
        output_template = os.path.join(output_dir, f"{safe_filename}.%(ext)s")
        
        logger.info(f"Downloading audio from {youtube_url}")
        logger.info(f"Output will be saved as: {safe_filename}.*")
        
        process = subprocess.run(
            ['yt-dlp', 
             '-f', 'bestaudio',  # Best audio format
             '--no-playlist',    # Don't download playlists
             '--progress',       # Show progress
             '-o', 
             output_template,  # Output filename template
             youtube_url],       # URL to download
            capture_output=True, # Capture stdout and stderr
            text=True,           # Return strings rather than bytes
            check=False          # Don't raise exception on non-zero exit
        )
        
        if process.returncode != 0:
            logger.error(f"yt-dlp failed with exit code {process.returncode}")
            logger.error(f"Error: {process.stderr}")
            return None
            
        downloaded_files = [f for f in os.listdir(output_dir) if f.startswith(safe_filename)]
        if not downloaded_files:
            logger.error("Download succeeded but file not found")
            return None
                
        downloaded_file = os.path.join(output_dir, downloaded_files[0])
        logger.info(f"Successfully downloaded file: {downloaded_file}")
        return downloaded_file
                
    except Exception as e:
        logger.error(f"Error downloading {youtube_url}: {str(e)}")
        return None


def process_episode(csv_path, output_dir):
    episode = get_episode(csv_path)
    if not episode:
        return None
        
    downloaded_file = download_episode(episode['url'], output_dir, episode)
    if not downloaded_file:
        logger.error(f"Failed to download episode {episode['season']}x{episode['episode_number']}")
        return None
        
    update_result = update_episode_status(csv_path, episode['index'], 'downloaded', True)
    if not update_result:
        logger.warning(f"Failed to update CSV status for episode {episode['season']}x{episode['episode_number']}")
    
    return downloaded_file


if __name__ == "__main__":
    csv_path = "downloader\\test_dataset.csv"
    output_dir = "downloaded_audio"
    
    downloaded_file = process_episode(csv_path, output_dir)
    
    if downloaded_file:
        logger.info(f"Downloaded file: {downloaded_file}")
    else:
        logger.info("No new episodes to download or download failed")
    