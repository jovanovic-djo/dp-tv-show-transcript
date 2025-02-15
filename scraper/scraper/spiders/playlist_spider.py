import scrapy
import json
import csv

class PlaylistSpider(scrapy.Spider):
    name = 'playlist'
    season_playlists = {
        1 : 'https://www.youtube.com/watch?v=McwPB-eQ2BY&list=PLACTVlX7-E7rq5Ghz0ll5sARODdIGljLK',
        2 : 'https://www.youtube.com/watch?v=MroqCKWf8SY&list=PLACTVlX7-E7oyZ9QGPqFVYmXX0npYN9tZ',
        3 : 'https://www.youtube.com/watch?v=K1ZqPEmk2Ho&list=PLACTVlX7-E7ot5AxkiGvuy4qem8nM-Mo6',
        4 : 'https://www.youtube.com/watch?v=hRQq4iSLAi8&list=PLACTVlX7-E7qP5XYTd7MsqgeewRPlw4HR',
        5 : 'https://www.youtube.com/watch?v=ygSDsQhV7aI&list=PLACTVlX7-E7rBAqGs_bgQDDJNZgwRpVKI',
        6.1 : 'https://www.youtube.com/watch?v=0UHpZ9YlOeQ&list=PLACTVlX7-E7ovvwkDQn2B4aRyQf0E-Ecb',
        6.2 : 'https://www.youtube.com/watch?v=W53ttgL7yJg&list=PLACTVlX7-E7o_dbXQophqz_3dhnZFk2i7',
        7.1 : 'https://www.youtube.com/watch?v=2CLFTY7Kwbo&list=PLACTVlX7-E7o9lBOoNCZgPLqBsRlzV2f6',
        7.2 : 'https://www.youtube.com/watch?v=s_-mP5Ne0ps&list=PLACTVlX7-E7ovtPLoVkGceGx6537TGoW7',
        8 : 'https://www.youtube.com/watch?v=ZCFpz16dYYA&list=PLACTVlX7-E7rQIBED2Kfqk88nJL8iYpyw',
        9 : 'https://www.youtube.com/watch?v=EGi70GAvqek&list=PLACTVlX7-E7oEGoLBnXkL5yt5nnSAaWXw',
        10 : 'https://www.youtube.com/watch?v=_JywROwNlWE&list=PLACTVlX7-E7qpWXUMNNvGsWaSU9jep85J',
        11 : 'https://www.youtube.com/watch?v=6kKDnfbYx-4&list=PLACTVlX7-E7pbBjiq1d8c39N0MAfx7KPP',
        12 : 'https://www.youtube.com/watch?v=V3Ewvh21P2c&list=PLACTVlX7-E7p3mtr1Eds5KmZ0RIiESRv2',
        13 : 'https://www.youtube.com/watch?v=NLrI4plEi90&list=PLACTVlX7-E7oCmwHSwioJfFdH4OAH4NTl'
    }
    
    def __init__(self, playlist_url=None, *args, **kwargs):
        super(PlaylistSpider, self).__init__(*args, **kwargs)
        self.start_urls = [playlist_url] if playlist_url else []
        
        # Create/open CSV file
        self.csv_file = open('..\\..\\..\\data\\playlist_items.csv', 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.writer(self.csv_file)
        # Write header
        self.csv_writer.writerow(['title', 'url', 'season'])

    def parse(self, response):
        # Extract the initial data from the page
        for script in response.xpath('//script/text()'):
            if 'var ytInitialData = ' in script.get():
                data = script.get().split('var ytInitialData = ')[1].split(';</script>')[0]
                json_data = json.loads(data)
                
                # Navigate through the JSON structure to find playlist items
                try:
                    playlist_items = json_data['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'][0]['playlistVideoListRenderer']['contents']
                    
                    for item in playlist_items:
                        if 'playlistVideoRenderer' in item:
                            video = item['playlistVideoRenderer']
                            title = video['title']['runs'][0]['text']
                            video_id = video['videoId']
                            url = f'https://www.youtube.com/watch?v={video_id}'
                            
                            # Write to CSV
                            self.csv_writer.writerow([title, url])
                            
                            yield {
                                'title': title,
                                'url': url,
                            }
                except KeyError as e:
                    self.logger.error(f"Error parsing JSON structure: {e}")
    
    def closed(self, reason):
        # Close CSV file when spider is done
        self.csv_file.close()