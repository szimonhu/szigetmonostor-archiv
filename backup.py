# backup.py
import os
import re
import sys
from datetime import datetime
from pathlib import Path
import yt_dlp
from internetarchive import upload

# --- Konfiguráció ---
CHANNEL_URL = "https://www.youtube.com/@szigetmonostorhirei8482/videos"
DOWNLOAD_DIR = "downloads"
DOWNLOAD_ARCHIVE_FILE = "downloaded.txt"  # yt-dlp ide írja, mi lett már letöltve
IA_ITEM_PREFIX = "szigetmonostor-"  # archive.org item azonosító prefix
# --- vége konfiguráció ---

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def slugify(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:200]

def main():
    # --- Ideiglenes teszt: konkrét videó URL ---
    y_videos = [{
        'webpage_url': 'https://www.youtube.com/watch?v=JuTuSn1M0Rg',
        'title': 'Képviselő-testületi ülés 2025-10-27',
        'upload_date': '20251027',
        'id': 'JuTuSn1M0Rg'
    }]

    if not y_videos:
        print("Nincs 27.-i videó a csatornán.")
        return

    print(f"Tegnapi videók száma: {len(y_videos)}")

    # letöltési opciók
    ydl_opts_download = {
        'outtmpl': f'{DOWNLOAD_DIR}/%(upload_date)s-%(id)s-%(title).200s.%(ext)s',
        'download_archive': DOWNLOAD_ARCHIVE_FILE,
        'format': 'bestvideo+bestaudio/best',
        'retries': 3,
        'noplaylist': True,
        'merge_output_format': 'mp4',
    }

    with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
        for e in y_videos:
            url = e.get('webpage_url') or e.get('url')
            title = e.get('title') or 'video'
            upload_date = e.get('upload_date') or datetime.utcnow().strftime("%Y%m%d")
            safe_title = slugify(title)
            print(f"Letöltés: {title} ({url})")
            try:
                ydl.download([url])
            except Exception as ex:
                print("Letöltési hiba:", ex)
                continue

            # keressük meg a letöltött fájlt
            found = list(Path(DOWNLOAD_DIR).glob(f"{upload_date}-*-{title[:50]}*")) + \
                    list(Path(DOWNLOAD_DIR).glob(f"{upload_date}-*-{e.get('id')}*"))
            if not found:
                found = list(Path(DOWNLOAD_DIR).glob(f"{upload_date}-*.*"))

            for f in found:
                fpath = str(f)
                print("Feltöltés Archive.org-ra:", fpath)
                item_id = IA_ITEM_PREFIX + upload_date + "-" + safe_title
                metadata = {
                    'title': title,
                    'mediatype': 'movies',
                    'collection': 'opensource_movies',
                    'creator': 'Szigetmonostor – képviselő-testületi ülés',
                    'description': f'Archiválás: forrás YouTube csatorna {CHANNEL_URL}',
                    'subject': ['önkormányzat', 'testületi ülés', 'közadat'],
                }
                try:
                    upload(item_id, files=[fpath], metadata=metadata)
                    print("Feltöltés sikeres:", item_id)
                    # törlés helyi fájlok
                    try:
                        os.remove(fpath)
                        print("Helyi fájl törölve:", fpath)
                    except Exception as re:
                        print("Hiba helyi fájl törlésénél:", re)
                except Exception as up_e:
                    print("Feltöltési hiba az Archive.org felé:", up_e)

if __name__ == "__main__":
    main()
