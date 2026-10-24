# PikPak Downloader

PikPak Downloader is a Python tool and library for interacting with PikPak Cloud Drive API. It supports user authentication, file listing, offline task submission (magnet links, HTTP links), and high-speed multi-chunk file downloading with resume capability and progress bars.

## Features

- 🔐 **Authentication**: Easy login with username/password and auto-refreshing access tokens.
- 📁 **File Management**: List files and directory trees on PikPak.
- 🧲 **Offline Downloads**: Submit magnet, torrent, or HTTP direct links directly to PikPak cloud storage.
- ⬇️ **Resumable Downloader**: Fast chunked file streaming with `Range` header support for resuming interrupted downloads, accompanied by clean `tqdm` progress bars.
- 💻 **CLI & Library**: Use via command-line interface or directly as a Python package in your projects.

---

## Installation

1. Clone or download this repository.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

---

## CLI Usage Guide

You can run the CLI using `python cli.py` or `python3 cli.py`.

### 1. Login to PikPak

Authenticate with your PikPak credentials. Tokens will be cached at `~/.pikpak_credentials.json` for subsequent requests.

```bash
python cli.py login -u "your_email@example.com" -p "your_password"
```

### 2. List Files and Folders

List items in your root directory or inside a specific folder:

```bash
# Root directory
python cli.py ls

# Specific folder
python cli.py ls -f <folder_id>
```

### 3. Add Offline Download Task (Magnet / URL)

Add magnet or direct HTTP download tasks to PikPak cloud:

```bash
python cli.py add "magnet:?xt=urn:btih:..."

# Specify parent folder and file name
python cli.py add "https://example.com/file.zip" -f <folder_id> -n "file.zip"
```

### 4. Download File or Folder to Local Storage

Download files or whole folders from PikPak to your local machine:

```bash
python cli.py download <file_or_folder_id> -o ./downloads
```

---

## Python API Usage Example

You can also import `PikPakClient` and `Downloader` directly in your Python code:

```python
from pikpak_client import PikPakClient
from downloader import Downloader

# Initialize client and login
client = PikPakClient()
client.login("your_email@example.com", "your_password")

# List files
files = client.list_files()
print(files)

# Add offline task
task = client.add_file_url("magnet:?xt=urn:btih:...")

# Get file direct download link and download
download_url = client.get_download_url("file_id_here")
downloader = Downloader()
downloader.download_file(download_url, output_path="./my_file.mp4")
```

---

## Running Unit Tests

Run the test suite using `pytest`:

```bash
python3 -m pytest
```
