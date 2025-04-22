import pandas as pd
import yt_dlp


def download_episode(url, file_name):
    ydl_options = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }],
        'outtmpl': f'{file_name}.%(ext)s',
    }

    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        ydl.download([url])



def get_name(season, ep_number, ep_name):
    ep_name = ep_name.replace(" ", "_")
    s = "s" + str(season) + "ep" + str(ep_number) + "-" + ep_name
    return s


if __name__ == "__main__":
    csv_path = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\samples_dataset.csv"
    output_dir = "C:\\Users\\gatz0\\Desktop\\Projects\\dp-tv-show-transcript\\data\\samples\\audio"

    df = pd.read_csv(csv_path)

    for index, row in df.iterrows():
        file_name = get_name(row['season'], row['episode_number'], row['episode_name'])

        link = ''
        if row['downloaded'] == False:
            link = row['url']
        else:
            continue
        
        episode = download_episode(link, file_name)
        df.at[index, 'downloaded'] = True
        df.to_csv(csv_path)