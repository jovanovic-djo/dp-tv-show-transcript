import argparse
import re
from pathlib import Path

import pandas as pd
import yt_dlp


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "samples" / "samples_dataset.csv"
OUTPUT_DIR = ROOT / "data" / "samples" / "audio"


def download_episode(url, file_name, output_dir):
    # Keep YouTube's original audio stream (usually Opus in .webm), Whisper decodes it directly
    ydl_options = {
        'format': 'bestaudio/best',
        'outtmpl': str(Path(output_dir) / f'{file_name}.%(ext)s'),
    }

    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        ydl.download([url])


def get_name(season, ep_number, ep_name):
    ep_name = re.sub(r'[<>:"/\\|?*]', '', ep_name).strip()
    ep_name = ep_name.replace(" ", "_")
    s = "s" + str(season) + "ep" + str(ep_number) + "-" + ep_name
    return s


def load_dataset(csv_path):
    df = pd.read_csv(csv_path)
    df = df.loc[:, ~df.columns.str.startswith('Unnamed')]
    if 'downloaded' not in df.columns:
        df['downloaded'] = False
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download episode audio listed in a dataset CSV.")
    parser.add_argument("--csv", type=Path, default=CSV_PATH, help="dataset CSV, its 'downloaded' column tracks progress")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="where audio files are saved")
    parser.add_argument("--limit", type=int, default=None, help="download at most this many episodes")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    df = load_dataset(args.csv)

    downloaded_count = 0
    for index, row in df.iterrows():
        if row['downloaded'] == True:
            continue
        if args.limit is not None and downloaded_count >= args.limit:
            break

        file_name = get_name(row['season'], row['episode_number'], row['episode_name'])
        try:
            download_episode(row['url'], file_name, args.output_dir)
        except yt_dlp.utils.DownloadError as e:
            print(f"Skipping {file_name}: {e}")
            continue

        df.at[index, 'downloaded'] = True
        df.to_csv(args.csv, index=False)
        downloaded_count += 1
