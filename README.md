###### Project is still in progress

## Idea Behind the Project
### Making transcript of every episode for one of the most popular TV shows in the region "Državni Posao" (eng. smth. like "Government Job"). There is no similar project nor dataset out there. 

## Goal
### Possibilities are unlimited, for both analysis and general curiosity. 
#### Do you want to find your favorite joke? 
- Just search through the dataset.
#### Wanna watch all the occurrences of a certain character?
- Again, just search through the dataset
#### Interested in making any data analysis of the show?
- Once more, just go through the dataset.

## Help of the Community
### There is a certain possibility that this "one man" project would be done in 1-2 years.
### This is an open-source project, any help from the community is welcome.

## Methodology
### So far, one of the working steps would be the following:
- Scrape titles and links of each episode from YouTube. (yt-dlp, see "Scraping the Data" below)
- Download each episode using manually or using automation. (Selenium)
- Upload episode/Provide a link to the 3rd party tool which would generate a transcript of the episode, manually or with automation. (Selenium)
- Store episodes and extract valuable data from them into the main dataset.

## Scraping the Data
### The scraper collects episode metadata from the official YouTube channel, no browser needed.
```
pip install -r requirements.txt
python scraper/script.py
```
- Reads season playlists from `data/scraper_data/playlist_input.csv` (add a row there for each new season).
- Writes raw playlist data to `data/scraper_data/playlist_output.csv`.
- Writes parsed data to `data/clean_data/episodes.csv` and `data/clean_data/bonus_content.csv`.
- Also checks the channel for episodes that were uploaded but left out of the season playlists (skip with `--no-channel`).
- Run `python scraper/script.py --help` for all options. If YouTube changes break scraping, update yt-dlp first: `pip install -U yt-dlp`.

### _About future contributions_: Guidelines and detailed documentation will be uploaded in the near future.

## About the TV Show
### Main data about show:
- Show aired: 2012.
- Number of episodes ~2300+
- Views 790,000,000+
- Languages: Serbian
- Secondary languages: German, Hungarian, English, Chinese, Slovakian, Greek
- Number of seasons: 13



