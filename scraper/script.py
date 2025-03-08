from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

def scrape_youtube_playlist(url):
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--mute-audio")  # Mute audio to avoid any sound playing
    # Uncomment the line below if you want to run in headless mode (no browser UI)
    # chrome_options.add_argument("--headless")
    
    # Initialize the driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # Navigate to the YouTube playlist
        driver.get(url)
        
        # Wait for the page to load
        time.sleep(3)
        
        # Accept cookies if the dialog appears (common in some regions)
        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Accept') or contains(text(), 'Accept')]"))
            )
            cookie_button.click()
            time.sleep(1)
        except:
            print("No cookie consent needed or already accepted.")
        
        # Get the number of videos in the playlist (if available)
        try:
            video_count_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.style-scope.ytd-playlist-sidebar-primary-info-renderer"))
            )
            video_count_text = video_count_element.text
            if "videos" in video_count_text.lower():
                estimated_video_count = int(''.join(filter(str.isdigit, video_count_text)))
                print(f"Playlist contains approximately {estimated_video_count} videos")
            else:
                estimated_video_count = 100  # Default if we can't determine
                print("Could not determine exact video count, will attempt to load all videos")
        except:
            estimated_video_count = 100  # Default if we can't determine
            print("Could not determine video count, will attempt to load all videos")
        
        # Scroll to load all videos in the playlist
        # YouTube loads videos as you scroll down
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        videos_loaded = 0
        max_scroll_attempts = 20  # Limit scrolling attempts to avoid infinite loops
        
        for _ in range(max_scroll_attempts):
            # Scroll down to the bottom
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            
            # Wait for new videos to load
            time.sleep(2)
            
            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            
            # Count currently loaded videos
            current_videos = driver.find_elements(By.CSS_SELECTOR, "#content.style-scope.ytd-playlist-video-renderer")
            videos_loaded = len(current_videos)
            
            print(f"Loaded {videos_loaded} videos so far...")
            
            # Break condition: scroll height remains the same or we've loaded enough videos
            if new_height == last_height or videos_loaded >= estimated_video_count:
                break
                
            last_height = new_height
        
        # Collect video information
        video_elements = driver.find_elements(By.CSS_SELECTOR, "ytd-playlist-video-renderer.style-scope.ytd-playlist-video-list-renderer")
        
        videos = []
        for element in video_elements:
            try:
                # Get title
                title_element = element.find_element(By.CSS_SELECTOR, "#video-title")
                title = title_element.text.strip()
                
                # Get link
                link = title_element.get_attribute("href")
                
                videos.append({
                    "title": title,
                    "url": link
                })
            except Exception as e:
                print(f"Error extracting video info: {e}")
                continue
        
        return videos
        
    finally:
        # Always close the driver
        driver.quit()

def main():
    url = 'https://www.youtube.com/playlist?list=PLACTVlX7-E7rq5Ghz0ll5sARODdIGljLK'
    
    print(f"Scraping playlist: {url}")
    videos = scrape_youtube_playlist(url)
    
    print(f"\nFound {len(videos)} videos:")
    for i, video in enumerate(videos, 1):
        print(f"{i}. {video['title']}")
        print(f"   {video['url']}")
        print()
    
    # Save results to a JSON file
    with open("youtube_playlist_videos.json", "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=4)
    
    print(f"Results saved to youtube_playlist_videos.json")

if __name__ == "__main__":
    main()