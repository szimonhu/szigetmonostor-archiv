# backup.py
import os
import re
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import yt_dlp
from internetarchive import upload

# --- Konfiguráció (ha akarod, módosíthatod) ---
CHANNEL_URL = "https://www.youtube.com/@szigetmonostorhirei8482/streams"
DOWNLOAD_DIR = "downloads"
DOWNLOAD_ARCHIVE_FILE = "downloaded.txt"  # yt-dlp ide írja, mi lett már letöltve
# Archiv item prefix (archive.org-on belüli item azonosító kezdete)
IA_ITEM_PREFIX = "szigetmonostor-"  # ez + dátum + slug lesz az item neve
# --- vége konfiguráció ---

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def slugify(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:200]

def find_yesterdays_videos(info_entries):
    # céldátum
    target_date = datetime.strptime("20251027", "%Y%m%d").date()
    result = []
    for e in info_entries:
        ud = e.get('upload_date')
        if ud:
            d = datetime.strptime(ud, "%Y%m%d").date()
            # +-1 nap eltérés engedve
            if abs((d - target_date).days) <= 1:
                result.append(e)
    return result


def main():
    # 1) Lekérdezzük a csatornát (letöltés nélkül) az infókért
    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',  # gyorsabb: csak a playlist/index meta
        'skip_download': True,
        'dump_single_json': True,
        'simulate': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(CHANNEL_URL, download=False)
        except Exception as e:
            print("Hiba a csatorna lekérdezésekor:", e)
            sys.exit(1)

    # info lehet playlist-szerű (entries)
    entries = info.get('entries') or []
    # megtaláljuk a tegnapi dátumú videókat
    y_videos = find_yesterdays_videos(entries)
    if not y_videos:
        print("Nincs 27.-i videó a csatornán.")
        return

    print(f"Tegnapi videók száma: {len(y_videos)}")

    # letöltési opciók (download_archive miatt nem tölti le kétszer ugyanazt)
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

            # keressük meg a letöltött fájlt (a mintázatból)
            # egyszerű keresés a DOWNLOAD_DIR-ben a upload_date és title rész alapján
            found = list(Path(DOWNLOAD_DIR).glob(f"{upload_date}-*-{title[:50]}*")) + \
                    list(Path(DOWNLOAD_DIR).glob(f"{upload_date}-*-{e.get('id')}*"))
            # ha nem találtunk, vegyünk minden upload_date kezdetűt
            if not found:
                found = list(Path(DOWNLOAD_DIR).glob(f"{upload_date}-*.*"))

            for f in found:
                fpath = str(f)
                print("Feltöltés Archive.org-ra:", fpath)
                # build item identifier
                item_id = IA_ITEM_PREFIX + upload_date + "-" + safe_title
                # metadata példa
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
                    # ha sikeres, töröljük a helyi fájlt
                    try:
                        os.remove(fpath)
                        print("Helyi fájl törölve:", fpath)
                    except Exception as re:
                        print("Hiba helyi fájl törlésénél:", re)
                except Exception as up_e:
                    print("Feltöltési hiba az Archive.org felé:", up_e)

if __name__ == "__main__":
    main()
