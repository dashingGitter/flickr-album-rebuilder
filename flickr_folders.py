#!/usr/bin/env python3
r"""
Flickr Album Rebuilder + Timestamp Restorer

Requirements:
    py -m pip install tqdm pywin32

Example:
    py flickr_folders.py --zips "D:\FlickrDownloads" --meta "D:\FlickrAlbumsMetadata" --out "C:\FlickrAlbums" --temp "_temp"

"""

import os
import re
import json
import shutil
import zipfile
import argparse
from collections import defaultdict
from datetime import datetime
from tqdm import tqdm
import pywintypes
import win32file
import win32con

# =========================================================
# CONFIG
# =========================================================

MEDIA_EXTS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp',
    '.tiff', '.heic', '.webp',
    '.mp4', '.mov', '.avi', '.mkv'
}

# =========================================================
# HELPERS
# =========================================================

def sanitize(name: str) -> str:
    """
    Replace illegal Windows filename chars with underscore.
    """
    if not name:
        return "untitled_album"

    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()


def ensure_dir(path: str):
    """
    Create directory only if missing.
    """
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def clear_folder(folder: str):
    """
    Delete all contents inside folder.
    """
    if not os.path.isdir(folder):
        return

    for root, dirs, files in os.walk(folder, topdown=False):

        for f in files:
            try:
                os.remove(os.path.join(root, f))
            except:
                pass

        for d in dirs:
            try:
                shutil.rmtree(os.path.join(root, d))
            except:
                pass


def is_media_file(fname: str) -> bool:
    return os.path.splitext(fname)[1].lower() in MEDIA_EXTS


# =========================================================
# PHOTO ID EXTRACTION
# =========================================================

def extract_photo_id_from_filename(filename: str):
    """
    Extract Flickr photo ID from filename.

    Rules:
      1. Remove extension
      2. Remove trailing "_o" if present
      3. Take last underscore token
      4. If numeric -> return
      5. Else fallback regex search
    """

    base = os.path.splitext(filename)[0]

    # remove trailing _o
    if base.endswith("_o"):
        base = base[:-2]

    # take last underscore token
    if "_" in base:
        token = base.rsplit("_", 1)[-1]
    else:
        token = base

    if token.isdigit() and len(token) >= 6:
        return token

    # fallback regex
    m = re.search(r'\d{6,}', filename)

    if m:
        return m.group(0)

    return None


# =========================================================
# BUILD PHOTO ID MAP
# =========================================================

def build_pictureid_map(albums_json_path):

    pid_map = defaultdict(list)

    with open(albums_json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    albums = data.get("albums", [])

    for album in albums:

        title = album.get("title", "untitled_album")

        for pid in album.get("photos", []):

            pid_map[str(pid)].append(title)

    return pid_map


# =========================================================
# DATE/TIME HELPERS
# =========================================================

def load_date_taken(meta_folder, pid):
    """
    Read:
        photo_<pid>.json

    Return datetime object or None.
    """

    json_path = os.path.join(meta_folder, f"photo_{pid}.json")

    if not os.path.isfile(json_path):
        return None

    try:

        with open(json_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        date_taken = data.get("date_taken")

        if not date_taken:
            return None

        # Example:
        # "2020-01-05 14:03:02"

        dt = datetime.strptime(date_taken, "%Y-%m-%d %H:%M:%S")

        return dt

    except:
        return None


def apply_windows_file_dates(file_path, dt):
    """
    Set:
        Created
        Modified
        Accessed

    timestamps on Windows.
    """

    try:

        win_time = pywintypes.Time(dt)

        handle = win32file.CreateFile(
            file_path,
            win32con.GENERIC_WRITE,
            0,
            None,
            win32con.OPEN_EXISTING,
            0,
            None
        )

        win32file.SetFileTime(
            handle,
            win_time,  # creation
            win_time,  # access
            win_time   # modified
        )

        handle.close()

    except Exception as e:
        print(f"Timestamp update failed: {file_path}")
        print(str(e))


# =========================================================
# FILE COPY/MOVE HELPERS
# =========================================================

def move_or_handle_duplicate(src, dest, duplicates_dir):
    """
    Move file if possible.

    Duplicate rules:
        - same size -> ignore
        - different size -> move incoming file to Duplicates
    """

    if os.path.exists(dest):

        src_size = os.path.getsize(src)
        dest_size = os.path.getsize(dest)

        # same file
        if src_size == dest_size:
            try:
                os.remove(src)
            except:
                pass

            return "SKIPPED"

        # different file
        else:

            dup_dest = os.path.join(
                duplicates_dir,
                os.path.basename(src)
            )

            shutil.move(src, dup_dest)

            return "DUPLICATE"

    else:

        shutil.move(src, dest)

        return "MOVED"


# =========================================================
# PROCESS ZIP
# =========================================================

def process_zip(
    zip_path,
    temp_folder,
    pid_map,
    output_root,
    duplicates_dir,
    auto_upload_dir,
    meta_folder
):

    print(f"\nProcessing ZIP: {os.path.basename(zip_path)}")

    clear_folder(temp_folder)
    ensure_dir(temp_folder)

    # ---------------------------------------------
    # UNZIP
    # ---------------------------------------------

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(temp_folder)

    # ---------------------------------------------
    # FIND MEDIA FILES
    # ---------------------------------------------

    media_files = []

    for root, _, files in os.walk(temp_folder):

        for f in files:

            if is_media_file(f):

                media_files.append(
                    os.path.join(root, f)
                )

    # ---------------------------------------------
    # PROCESS FILES
    # ---------------------------------------------

    for fp in tqdm(media_files, desc="Processing Files", unit="file"):

        try:

            bname = os.path.basename(fp)

            pid = extract_photo_id_from_filename(bname)

            # -------------------------------------
            # MATCH ALBUMS
            # -------------------------------------

            matched_albums = []

            if pid:

                if pid in pid_map:

                    matched_albums = pid_map[pid]

            # -------------------------------------
            # AUTO UPLOAD
            # -------------------------------------

            if not matched_albums:

                dest = os.path.join(
                    auto_upload_dir,
                    bname
                )

                result = move_or_handle_duplicate(
                    fp,
                    dest,
                    duplicates_dir
                )

                # update timestamps
                if result == "MOVED":

                    dt = load_date_taken(meta_folder, pid)

                    if dt:
                        apply_windows_file_dates(dest, dt)

                continue

            # -------------------------------------
            # FIRST ALBUM = MOVE
            # -------------------------------------

            first_album = sanitize(matched_albums[0])

            first_album_folder = os.path.join(
                output_root,
                first_album
            )

            ensure_dir(first_album_folder)

            first_dest = os.path.join(
                first_album_folder,
                bname
            )

            result = move_or_handle_duplicate(
                fp,
                first_dest,
                duplicates_dir
            )

            # update timestamps
            if result == "MOVED":

                dt = load_date_taken(meta_folder, pid)

                if dt:
                    apply_windows_file_dates(first_dest, dt)

            # -------------------------------------
            # OTHER ALBUMS = COPY
            # -------------------------------------

            if result == "MOVED":

                for other_album in matched_albums[1:]:

                    other_album = sanitize(other_album)

                    other_folder = os.path.join(
                        output_root,
                        other_album
                    )

                    ensure_dir(other_folder)

                    other_dest = os.path.join(
                        other_folder,
                        bname
                    )

                    # duplicate logic
                    if os.path.exists(other_dest):

                        if os.path.getsize(other_dest) != os.path.getsize(first_dest):

                            dup_dest = os.path.join(
                                duplicates_dir,
                                bname
                            )

                            shutil.copy2(first_dest, dup_dest)

                    else:

                        shutil.copy2(
                            first_dest,
                            other_dest
                        )

                        # update timestamps on copies too
                        dt = load_date_taken(meta_folder, pid)

                        if dt:
                            apply_windows_file_dates(other_dest, dt)

        except Exception as e:

            print(f"\nprocessing error: {str(e)}")
            print(f"file: {fp}")

    # ---------------------------------------------
    # CLEAN TEMP
    # ---------------------------------------------

    clear_folder(temp_folder)


# =========================================================
# MAIN
# =========================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--zips", required=True)
    parser.add_argument("--meta", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--temp", required=True)

    args = parser.parse_args()

    zip_folder = os.path.abspath(args.zips)
    meta_folder = os.path.abspath(args.meta)
    output_root = os.path.abspath(args.out)
    temp_folder = os.path.abspath(args.temp)

    duplicates_dir = os.path.join(output_root, "Duplicates")
    auto_upload_dir = os.path.join(output_root, "Auto Upload")

    ensure_dir(output_root)
    ensure_dir(duplicates_dir)
    ensure_dir(auto_upload_dir)

    albums_json = os.path.join(
        meta_folder,
        "albums.json"
    )

    print("\nLoading albums.json ...")

    pid_map = build_pictureid_map(albums_json)

    print(f"Loaded {len(pid_map)} photo IDs")

    # ---------------------------------------------
    # FIND ZIP FILES
    # ---------------------------------------------

    zip_files = sorted([

        os.path.join(zip_folder, f)

        for f in os.listdir(zip_folder)

        if f.lower().endswith(".zip")

    ])

    print(f"Found {len(zip_files)} ZIP files")

    # ---------------------------------------------
    # PROCESS EACH ZIP
    # ---------------------------------------------

    for zf in zip_files:

        process_zip(
            zf,
            temp_folder,
            pid_map,
            output_root,
            duplicates_dir,
            auto_upload_dir,
            meta_folder
        )

    print("\nDONE")


# =========================================================

if __name__ == "__main__":
    main()