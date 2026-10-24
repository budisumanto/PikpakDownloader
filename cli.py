import argparse
import os
import sys
from pikpak_client import PikPakClient, PikPakError
from downloader import Downloader


def handle_login(args, client):
    username = args.username
    password = args.password
    try:
        data = client.login(username=username, password=password)
        print(f"Login successful for user {client.username}!")
    except PikPakError as e:
        print(f"Error logging in: {e}", file=sys.stderr)
        sys.exit(1)


def handle_ls(args, client):
    parent_id = args.folder_id or ""
    try:
        result = client.list_files(parent_id=parent_id)
        files = result.get("files", [])
        if not files:
            print("No files found.")
            return

        print(f"{'ID':<28} {'TYPE':<10} {'SIZE':<12} {'NAME'}")
        print("-" * 70)
        for f in files:
            kind = "Folder" if f.get("kind") == "drive#folder" else "File"
            size = f.get("size", "0")
            try:
                size_num = int(size)
                if size_num >= 1024 * 1024 * 1024:
                    size_str = f"{size_num / (1024**3):.2f} GB"
                elif size_num >= 1024 * 1024:
                    size_str = f"{size_num / (1024**2):.2f} MB"
                elif size_num >= 1024:
                    size_str = f"{size_num / 1024:.2f} KB"
                else:
                    size_str = f"{size_num} B"
            except (ValueError, TypeError):
                size_str = str(size)

            print(f"{f.get('id'):<28} {kind:<10} {size_str:<12} {f.get('name')}")

    except PikPakError as e:
        print(f"Error listing files: {e}", file=sys.stderr)
        sys.exit(1)


def handle_add(args, client):
    url = args.url
    parent_id = args.folder_id or ""
    name = args.name or ""
    try:
        result = client.add_file_url(url, parent_id=parent_id, name=name)
        task = result.get("task", {})
        task_id = task.get("id") or result.get("file", {}).get("id")
        print(f"Task added successfully! Task/File ID: {task_id}")
    except PikPakError as e:
        print(f"Error adding task: {e}", file=sys.stderr)
        sys.exit(1)


def _download_single_file(client, downloader, file_id, output_dir, name_override=None):
    file_info = client.get_file_info(file_id)
    if file_info.get("kind") == "drive#folder":
        print(f"Downloading folder content: {file_info.get('name')} ({file_id})")
        folder_output_dir = os.path.join(output_dir, file_info.get("name", "folder"))
        os.makedirs(folder_output_dir, exist_ok=True)
        sub_files = client.list_files(parent_id=file_id).get("files", [])
        for sub in sub_files:
            _download_single_file(client, downloader, sub["id"], folder_output_dir)
        return

    file_name = name_override or file_info.get("name", file_id)
    print(f"Fetching download link for '{file_name}'...")
    download_url = client.get_download_url(file_id)
    print(f"Starting download: {file_name}")
    downloader.download_file(download_url, output_dir, custom_filename=file_name)


def handle_download(args, client):
    file_id = args.file_id
    output_dir = args.output or "."
    downloader = Downloader()
    try:
        _download_single_file(client, downloader, file_id, output_dir)
        print("Download completed successfully!")
    except Exception as e:
        print(f"Error downloading file: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="PikPak Downloader CLI Tool")
    subparsers = parser.add_parsers(dest="command", help="Available commands")

    # login command
    login_parser = subparsers.add_parser("login", help="Log in to PikPak")
    login_parser.add_argument("-u", "--username", required=True, help="PikPak account username/email")
    login_parser.add_argument("-p", "--password", required=True, help="PikPak account password")

    # ls command
    ls_parser = subparsers.add_parser("ls", help="List files and folders")
    ls_parser.add_argument("-f", "--folder-id", help="Parent folder ID (optional)", default="")

    # add command
    add_parser = subparsers.add_parser("add", help="Add offline task (Magnet, HTTP link, etc.)")
    add_parser.add_argument("url", help="URL or magnet link to add")
    add_parser.add_argument("-f", "--folder-id", help="Target folder ID in PikPak", default="")
    add_parser.add_argument("-n", "--name", help="Custom name for the file", default="")

    # download command
    dl_parser = subparsers.add_parser("download", help="Download file or folder to local storage")
    dl_parser.add_argument("file_id", help="PikPak file or folder ID")
    dl_parser.add_argument("-o", "--output", help="Local directory path to save file", default=".")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    client = PikPakClient()

    if args.command == "login":
        handle_login(args, client)
    elif args.command == "ls":
        handle_ls(args, client)
    elif args.command == "add":
        handle_add(args, client)
    elif args.command == "download":
        handle_download(args, client)


if __name__ == "__main__":
    main()
