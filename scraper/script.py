import csv
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd

def scrape_youtube_playlist(url, season):
    """
    Scrape YouTube playlist videos
    
    Args:
        url: YouTube playlist URL
        season: Season number from input CSV
        
    Returns:
        List of dictionaries containing video information
    """
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
    
    # Uncomment for headless mode if needed
    # chrome_options.add_argument("--headless")
    
    # Initialize the driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # Set window size to a larger size to see more videos
        driver.set_window_size(1920, 1080)
        
        # Navigate to the YouTube playlist
        driver.get(url)
        
        # Wait for the page to load
        time.sleep(5)
        
        # Accept cookies if the dialog appears
        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Accept') or contains(text(), 'Accept')]"))
            )
            cookie_button.click()
            time.sleep(1)
        except:
            print("No cookie consent needed or already accepted.")
        
        # Wait for the playlist container to load
        try:
            playlist_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-playlist-video-list-renderer"))
            )
        except:
            print(f"Could not find the playlist container for season {season}")
            return []
            
        # Get the number of videos in the playlist (if available)
        try:
            video_count_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.style-scope.ytd-playlist-sidebar-primary-info-renderer"))
            )
            video_count_text = video_count_element.text
            if "videos" in video_count_text.lower():
                estimated_video_count = int(''.join(filter(str.isdigit, video_count_text)))
                print(f"Season {season} playlist contains approximately {estimated_video_count} videos")
            else:
                estimated_video_count = 100  # Default if we can't determine
                print(f"Could not determine exact video count for season {season}, will attempt to load all videos")
        except:
            estimated_video_count = 100  # Default if we can't determine
            print(f"Could not determine video count for season {season}, will attempt to load all videos")
        
        # Enhanced scrolling strategy - KEEPING ORIGINAL LOGIC
        videos_loaded = 0
        last_videos_loaded = 0
        max_scroll_attempts = 60  # Increased for larger playlists
        no_change_count = 0  # Count consecutive attempts with no new videos
        
        for i in range(max_scroll_attempts):
            # Method 1: Scroll to bottom of page first to ensure playlist is in view
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Method 2: Focus on the playlist container
            driver.execute_script("arguments[0].scrollIntoView();", playlist_container)
            time.sleep(1)
            
            # Method 3: Aggressive scrolling within the playlist container
            driver.execute_script("""
                var playlistContent = document.querySelector('ytd-playlist-video-list-renderer #contents');
                if (playlistContent) {
                    // Scroll in larger steps
                    playlistContent.scrollTop += 5000;
                    // Also try setting to maximum
                    setTimeout(function() { 
                        playlistContent.scrollTop = playlistContent.scrollHeight;
                    }, 500);
                }
            """)
            
            # Wait longer for videos to load
            time.sleep(3)
            
            # Method 4: Try clicking "Show more" button if it exists
            try:
                show_more_button = driver.find_element(By.CSS_SELECTOR, "button.yt-spec-button-shape-next.yt-spec-button-shape-next--text")
                if "show more" in show_more_button.text.lower():
                    show_more_button.click()
                    print(f"Season {season} - Clicked 'Show more' button")
                    time.sleep(3)
            except:
                pass
            
            # Count currently loaded videos
            current_videos = driver.find_elements(By.CSS_SELECTOR, "ytd-playlist-video-renderer")
            current_count = len(current_videos)
            
            print(f"Season {season} - Scroll attempt {i+1}/{max_scroll_attempts}: Loaded {current_count} videos so far...")
            
            # Check if we've loaded new videos
            if current_count > videos_loaded:
                videos_loaded = current_count
                no_change_count = 0  # Reset the counter
            else:
                no_change_count += 1
            
            # Break conditions:
            # 1. We've loaded all expected videos
            # 2. No new videos for several consecutive attempts
            if current_count >= estimated_video_count or no_change_count >= 5:
                print(f"Season {season} - No more videos being loaded for {no_change_count} attempts, stopping scroll.")
                break
                
            # Every 10 attempts, try refreshing the page to overcome any loading issues
            if i > 0 and i % 10 == 0 and current_count < estimated_video_count:
                print(f"Season {season} - Refreshing page to try to load more videos")
                driver.refresh()
                time.sleep(5)
                
                # Wait for the playlist container to reload
                try:
                    playlist_container = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-playlist-video-list-renderer"))
                    )
                except:
                    print(f"Could not find the playlist container after refresh for season {season}")
                    break
        
        # Final count of loaded videos
        video_elements = driver.find_elements(By.CSS_SELECTOR, "ytd-playlist-video-renderer")
        print(f"Season {season} - Final video count: {len(video_elements)}")
        
        # Collect video information
        videos = []
        for index, element in enumerate(video_elements):
            try:
                # Get title
                title_element = element.find_element(By.CSS_SELECTOR, "#video-title")
                title = title_element.text.strip()
                
                # Get link
                link = title_element.get_attribute("href")
                
                # Get video length - Try multiple selectors
                length = ""
                
                # First attempt: Look for the badge-shape-wiz__text div
                try:
                    length_element = element.find_element(By.CSS_SELECTOR, "div.badge-shape-wiz__text")
                    length = length_element.text.strip()
                    print(f"Found length via badge-shape-wiz__text: '{length}' for video {index+1}")
                except:
                    # Second attempt: Try the thumbnail overlay time status
                    try:
                        length_element = element.find_element(By.CSS_SELECTOR, "span.style-scope.ytd-thumbnail-overlay-time-status-renderer")
                        length = length_element.text.strip()
                        print(f"Found length via thumbnail overlay: '{length}' for video {index+1}")
                    except:
                        # Third attempt: Try different variation of time status renderer
                        try:
                            length_element = element.find_element(By.CSS_SELECTOR, "ytd-thumbnail-overlay-time-status-renderer span")
                            length = length_element.text.strip()
                            print(f"Found length via alternative selector: '{length}' for video {index+1}")
                        except:
                            # Fourth attempt: Try general time display
                            try:
                                length_element = element.find_element(By.XPATH, ".//span[contains(@class, 'time')]")
                                length = length_element.text.strip()
                                print(f"Found length via xpath: '{length}' for video {index+1}")
                            except:
                                print(f"Could not find length for video {index+1}: {title}")
                
                # Add to the list if we have both title and link
                if title and link:
                    videos.append({
                        "season": season,
                        "title": title,
                        "episode_number": "",  # To be filled later
                        "episode_name": "",    # To be filled later
                        "date": "",            # To be filled later
                        "length": length,      # Extracted video length
                        "url": link
                    })
            except Exception as e:
                print(f"Error extracting video info in season {season}, video {index+1}: {e}")
                continue
        
        return videos
        
    finally:
        # Always close the driver
        driver.quit()

def process_csv(input_file, output_file):
    """
    Process the input CSV file containing playlist URLs and seasons
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file
    """
    # Ensure directories exist
    os.makedirs(os.path.dirname(input_file), exist_ok=True)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Read the input CSV file
    try:
        df = pd.read_csv(input_file)
        print(f"Successfully loaded {len(df)} rows from {input_file}")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Clean column names and values
    df.columns = [col.strip() for col in df.columns]
    if 'url' in df.columns:
        df['url'] = df['url'].str.strip("'")
    
    # Initialize list to store all video data
    all_videos = []
    
    # Process each playlist
    for _, row in df.iterrows():
        season = row['season']
        url = row['url']
        
        print(f"\nProcessing Season {season}: {url}")
        videos = scrape_youtube_playlist(url, season)
        
        print(f"Found {len(videos)} videos for Season {season}")
        all_videos.extend(videos)
    
    # Convert to DataFrame and save to CSV
    result_df = pd.DataFrame(all_videos)
    
    # Ensure output DataFrame has all required columns in the correct order
    required_columns = ['season', 'title', 'episode_number', 'episode_name', 'date', 'length', 'url']
    for col in required_columns:
        if col not in result_df.columns:
            result_df[col] = ""
    
    # Reorder columns to match required output
    result_df = result_df[required_columns]
    
    # Save to CSV
    result_df.to_csv(output_file, index=False)
    print(f"\nSuccessfully saved {len(result_df)} videos to {output_file}")
    print(f"Data was saved with these columns: {', '.join(result_df.columns)}")
    
    # Print some statistics about the length column
    length_stats = result_df['length'].value_counts().head(10)
    print(f"\nTop 10 length values:\n{length_stats}")
    print(f"Number of videos with length: {result_df['length'].notna().sum()}")
    print(f"Number of videos without length: {result_df['length'].isna().sum()}")

def main():
    input_file = "..\\data\\scraper_data\\test_input.csv"
    output_file = "..\\data\\scraper_data\\test_output.csv"
    
    # Make sure paths use the correct directory separator for the OS
    input_file = os.path.normpath(input_file)
    output_file = os.path.normpath(output_file)
    
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    
    # Process the CSV file
    process_csv(input_file, output_file)

if __name__ == "__main__":
    main()