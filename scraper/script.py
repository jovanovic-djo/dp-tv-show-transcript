from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

url = 'https://www.youtube.com/watch?v=McwPB-eQ2BY&list=PLACTVlX7-E7rq5Ghz0ll5sARODdIGljLK'
driver.get(url)

time.sleep(5)  

titles = driver.find_elements(By.CSS_SELECTOR, "yt-formatted-string.style-scope.ytd-playlist-video-renderer")

video_titles = [title.text for title in titles if title.text.strip()]
print(video_titles)

driver.quit()
