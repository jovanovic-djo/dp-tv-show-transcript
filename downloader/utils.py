import os
import subprocess
import pandas as pd

def get_episode_to_download(path):
    df = pd.read_csv(path)

    not_downloaded = df[df['downloaded'] == False]

    if not_downloaded.empty:
        return None
    
    episode = not_downloaded.iloc[0].to_dict()

    index = not_downloaded.index[0]
    episode['index'] = index

    return episode


def download_episode(youtube_url, output_dir):

    os.makedirs(output_dir, exist_ok=True)

    video_id = youtube_url.split("v=")[-1].split("&")[0]
    safe_filename = f"video_{video_id}"
    output_template = os.path.join(output_dir, f"{safe_filename}.%(ext)s")
        
    process = subprocess.run(
        ['yt-dlp', '-f', 'bestaudio', '--no-playlist', '--progress', '-o', output_template, youtube_url],
        capture_output=True,
        text=True, 
        check=False 
    )
   
    if process.returncode != 0:
        return None
        
    downloaded_files = [f for f in os.listdir(output_dir) if f.startswith(f"video_{video_id}")]
    if not downloaded_files:
        return None
            
    downloaded_file = os.path.join(output_dir, downloaded_files[0])
    return downloaded_file
                


if __name__ == "__main__":
    test_link = "https://www.youtube.com/watch?v=McwPB-eQ2BY"
    output_dir = "downloaded_audio"
    input_dataset = "test_dataset.csv"
    
    downloaded_file = download_episode(test_link, output_dir)

    