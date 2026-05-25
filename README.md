# Flickr Album Rebuilder

A Python utility to reconstruct Flickr albums locally from a Flickr data export.

This script:

- Reads Flickr `albums.json`
- Rebuilds album folders
- Organizes photos/videos into albums
- Restores original `date_taken` timestamps from Flickr metadata
- Handles duplicate detection
- Supports incremental ZIP processing
- Processes one ZIP at a time to reduce disk usage

---

# Features

- Reconstructs Flickr albums into folders
- Supports:
  - JPG
  - PNG
  - GIF
  - HEIC
  - MP4
  - AVI
  - MOV
  - MKV
  - and more
- Restores:
  - Created Date
  - Modified Date
  - Accessed Date
- Duplicate protection
- Handles photos in multiple albums
- Handles "Auto Upload" / ungrouped files
- Windows-compatible
- Low temporary disk usage

---

# Requirements

Install Python 3.10+.

Install dependencies:

```powershell
py -m pip install tqdm pywin32
```

---

# Required Folder Structure

Create the following folders:

```text
FlickrDownloads/
FlickrAlbumsMetadata/
FlickrAlbums/
_temp_flickr/
```

---

# Folder Details

## 1. FlickrDownloads

Place all Flickr ZIP exports here.

Example:

```text
data-download-1.zip
data-download-2.zip
...
data-download-82.zip
```

---

## 2. FlickrAlbumsMetadata

Place Flickr metadata JSON files here.

Must contain:

```text
albums.json
```

and all:

```text
photo_<photoid>.json
```

Example:

```text
photo_49491227411.json
photo_7618135812.json
```

---

## 3. FlickrAlbums

Output folder.

The script creates album folders here automatically.

Example:

```text
FlickrAlbums/
    Vacation 2020/
    Family/
    Auto Upload/
```

---

## 4. _temp_flickr

Temporary extraction folder used during processing.

The script automatically clears this folder between ZIPs.

---

# Usage

Example:

```powershell
py flickr_folders.py ^
  --zips "D:\FlickrDownloads" ^
  --meta "D:\FlickrAlbumsMetadata" ^
  --out "D:\FlickrAlbums" ^
  --temp "D:\_temp_flickr"
```

---

# Important Notes

## Windows Path Lengths

Very long album names and filenames may exceed Windows path limits.

Recommended:

Use short root folders like:

```text
D:\FlickrAlbums
D:\FlickrDownloads
```

instead of deeply nested folders.

---

## Duplicate Handling

If duplicate files are detected:

- Same size → ignored
- Different size → copied into:

```text
Duplicates/
```

---

# Incremental Processing

You can process ZIPs in batches.

Example:

- First 10 ZIPs today
- Next 10 ZIPs tomorrow

The script safely reuses existing album folders.

---

# Disclaimer

This project is unofficial and is not affiliated with Flickr or SmugMug.