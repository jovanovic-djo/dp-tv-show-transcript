import argparse
import re
import unicodedata
from pathlib import Path

import pandas as pd
import yt_dlp


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "scraper_data" / "playlist_input.csv"
OUTPUT_FILE = ROOT / "data" / "scraper_data" / "playlist_output.csv"
CLEAN_DIR = ROOT / "data" / "clean_data"
CHANNEL_URL = "https://www.youtube.com/@DrzavniPosaoSerija/videos"

SHOW_PREFIX = "DRŽAVNI POSAO"
EPISODE_KEY = "Ep."
COLUMNS = ["season", "title", "episode_number", "episode_name", "date", "length", "url"]

EPISODE_RE = re.compile(r"Ep\.\s*(\d+)\s*:\s*")
DATE_RE = re.compile(r"\(\s*(\d{2}\.\d{2}\.\d{4}\.)\s*\)")


def fetch_entries(url):
    ydl_options = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        info = ydl.extract_info(url, download=False)

    return [entry for entry in info.get("entries", []) if entry and entry.get("id")]


def format_length(seconds):
    if seconds is None:
        return ""

    hours, rest = divmod(int(seconds), 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def clean_title(title):
    return " ".join(unicodedata.normalize("NFC", title).split())


def video_url(video_id):
    return f"https://www.youtube.com/watch?v={video_id}"


def scrape_youtube_playlist(url, season):
    list_id = re.search(r"list=([^&]+)", url).group(1)
    videos = []

    for index, entry in enumerate(fetch_entries(url), start=1):
        videos.append({
            "season": season,
            "title": clean_title(entry["title"]),
            "episode_number": "",
            "episode_name": "",
            "date": "",
            "length": format_length(entry.get("duration")),
            "url": f"{video_url(entry['id'])}&list={list_id}&index={index}",
        })

    print(f"Season {season}: found {len(videos)} videos")
    return videos


def parse_title(title):
    """Return (episode_number, episode_name, date) parsed from a video title."""
    dates = list(DATE_RE.finditer(title))
    date = dates[-1].group(1) if dates else ""

    episode = EPISODE_RE.search(title)
    if not episode:
        return "", "", date

    name_end = len(title)
    for match in dates:
        if match.start() > episode.end():
            name_end = match.start()
            break

    return int(episode.group(1)), title[episode.end():name_end].strip(), date


def clean(raw_df):
    df = raw_df.copy()
    df["url"] = df["url"].str.split("&").str[0]

    parsed = df["title"].apply(parse_title)
    df["episode_number"] = parsed.str[0]
    df["episode_name"] = parsed.str[1]
    df["date"] = parsed.str[2]

    is_episode = df["title"].str.contains(EPISODE_KEY, regex=False)
    return df[is_episode].reset_index(drop=True), df[~is_episode].reset_index(drop=True)


def add_channel_episodes(episodes_df, channel_url):
    """Add episodes that are uploaded on the channel but missing from every season playlist."""
    known_ids = set(episodes_df["url"].str.extract(r"v=([^&]+)")[0])
    known_numbers = set(episodes_df["episode_number"])
    rows = episodes_df.to_dict("records")

    added = 0
    for entry in fetch_entries(channel_url):
        title = clean_title(entry["title"])
        if entry["id"] in known_ids or not title.startswith(SHOW_PREFIX) or EPISODE_KEY not in title:
            continue

        number, name, date = parse_title(title)
        if number == "" or number in known_numbers:
            continue

        position = next((i for i, row in enumerate(rows) if row["episode_number"] > number), len(rows))
        season = rows[position - 1]["season"] if position > 0 else rows[0]["season"]
        if position < len(rows) and rows[position]["season"] != season:
            print(f"Ep.{number} falls between seasons {season} and {rows[position]['season']}, assigned to season {season}")

        rows.insert(position, {
            "season": season,
            "title": title,
            "episode_number": number,
            "episode_name": name,
            "date": date,
            "length": format_length(entry.get("duration")),
            "url": video_url(entry["id"]),
        })
        known_numbers.add(number)
        added += 1
        print(f"Added Ep.{number}: {name} (not in any playlist)")

    print(f"Channel check: added {added} episodes missing from playlists")
    return pd.DataFrame(rows, columns=COLUMNS)


def read_playlists(input_file):
    df = pd.read_csv(input_file)
    df.columns = [col.strip() for col in df.columns]
    df["url"] = df["url"].str.strip().str.strip("'")
    return df[["season", "url"]]


def save_csv(df, path, index=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8", lineterminator="\n")
    print(f"Saved {len(df)} rows to {path}")


def main():
    parser = argparse.ArgumentParser(description="Scrape Državni posao episode metadata from YouTube.")
    parser.add_argument("--input", type=Path, default=INPUT_FILE, help="CSV with season playlist URLs")
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE, help="raw scraped playlist data")
    parser.add_argument("--clean-dir", type=Path, default=CLEAN_DIR, help="where episodes.csv and bonus_content.csv are written")
    parser.add_argument("--channel", default=CHANNEL_URL, help="channel videos URL used to find episodes missing from playlists")
    parser.add_argument("--no-channel", action="store_true", help="skip the channel check")
    args = parser.parse_args()

    all_videos = []
    for _, row in read_playlists(args.input).iterrows():
        all_videos.extend(scrape_youtube_playlist(row["url"], row["season"]))

    raw_df = pd.DataFrame(all_videos, columns=COLUMNS)
    save_csv(raw_df, args.output)

    episodes_df, bonus_df = clean(raw_df)
    if not args.no_channel:
        episodes_df = add_channel_episodes(episodes_df, args.channel)

    save_csv(episodes_df, args.clean_dir / "episodes.csv", index=True)
    save_csv(bonus_df, args.clean_dir / "bonus_content.csv", index=True)


if __name__ == "__main__":
    main()
