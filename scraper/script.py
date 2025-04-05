from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import os
import time
import pandas as pd


def scrape_youtube_playlist(url, season):
    chrome_options = Options()
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.set_window_size(1920, 1080)
        
        time.sleep(5)
        
        try:
            playlist_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-playlist-video-list-renderer"))
            )
        except:
            print(f"Could not find the playlist container for season {season}")
            return []
            
        try:
            video_count_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.style-scope.ytd-playlist-sidebar-primary-info-renderer"))
            )
            video_count_text = video_count_element.text
            if "videos" in video_count_text.lower():
                estimated_video_count = int(''.join(filter(str.isdigit, video_count_text)))
                print(f"Season {season} playlist contains approximately {estimated_video_count} videos")
            else:
                estimated_video_count = 100
                print(f"Could not determine exact video count for season {season}, will attempt to load all videos")
        except:
            estimated_video_count = 100
            print(f"Could not determine video count for season {season}, will attempt to load all videos")

        videos_loaded = 0
        max_scroll_attempts = 60
        no_change_count = 0
        
        for i in range(max_scroll_attempts):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
            time.sleep(3)
            
            current_videos = driver.find_elements(By.CSS_SELECTOR, "ytd-playlist-video-renderer")
            current_count = len(current_videos)
            
            print(f"Season {season} - Scroll attempt {i+1}/{max_scroll_attempts}: Loaded {current_count} videos so far...")
            
            if current_count > videos_loaded:
                videos_loaded = current_count
                no_change_count = 0
            else:
                no_change_count += 1
            
            
            if current_count >= estimated_video_count or no_change_count >= 5:
                print(f"Season {season} - No more videos being loaded for {no_change_count} attempts, stopping scroll.")
                break
                
            if i > 0 and i % 10 == 0 and current_count < estimated_video_count:
                print(f"Season {season} - Refreshing page to try to load more videos")
                driver.refresh()
                time.sleep(5)
                
                try:
                    playlist_container = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-playlist-video-list-renderer"))
                    )
                except:
                    print(f"Could not find the playlist container after refresh for season {season}")
                    break
        
        video_elements = driver.find_elements(By.CSS_SELECTOR, "ytd-playlist-video-renderer")
        print(f"Season {season} - Final video count: {len(video_elements)}")
        
        videos = []
        for index, element in enumerate(video_elements):
            try:
                title_element = element.find_element(By.CSS_SELECTOR, "#video-title")
                title = title_element.text.strip()
                
                link = title_element.get_attribute("href")
                length = ""
                
                try:
                    length_element = element.find_element(By.CSS_SELECTOR, "div.badge-shape-wiz__text")
                    length = length_element.text.strip()
                except:
                    print(f"Could not find length for video {index+1}: {title}")
                
                if title and link:
                    videos.append({
                        "season": season,
                        "title": title,
                        "episode_number": "",
                        "episode_name": "",
                        "date": "",
                        "length": length,
                        "url": link
                    })
            except Exception as e:
                print(f"Error extracting video info in season {season}, video {index+1}: {e}")
                continue
        
        return videos
        
    finally:
        driver.quit()

def process_csv(input_file, output_file):
    os.makedirs(os.path.dirname(input_file), exist_ok=True)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    try:
        df = pd.read_csv(input_file)
        print(f"Successfully loaded {len(df)} rows from {input_file}")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    df.columns = [col.strip() for col in df.columns]
    if 'url' in df.columns:
        df['url'] = df['url'].str.strip("'")
    
    all_videos = []
    
    for _, row in df.iterrows():
        season = row['season']
        url = row['url']
        
        print(f"\nProcessing Season {season}: {url}")
        videos = scrape_youtube_playlist(url, season)
        
        print(f"Found {len(videos)} videos for Season {season}")
        all_videos.extend(videos)
    
    result_df = pd.DataFrame(all_videos)
    
    required_columns = ['season', 'title', 'episode_number', 'episode_name', 'date', 'length', 'url']
    for col in required_columns:
        if col not in result_df.columns:
            result_df[col] = ""
    
    result_df = result_df[required_columns]
    
    result_df.to_csv(output_file, index=False)
    print(f"\nSuccessfully saved {len(result_df)} videos to {output_file}")
    print(f"Data was saved with these columns: {', '.join(result_df.columns)}")
    

def main():
    input_file = "..\\data\\scraper_data\\playlist_input.csv"
    output_file = "..\\data\\scraper_data\\playlist_output.csv"
    
    input_file = os.path.normpath(input_file)
    output_file = os.path.normpath(output_file)
    
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    
    process_csv(input_file, output_file)

if __name__ == "__main__":
    main()