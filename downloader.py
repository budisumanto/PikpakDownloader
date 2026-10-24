import os
import requests
from tqdm import tqdm


class Downloader:
    """Utility class for downloading files with chunked streaming, resume capability, and progress bar."""

    def __init__(self, chunk_size=8192, session=None):
        self.chunk_size = chunk_size
        self.session = session or requests.Session()

    def download_file(self, url, output_path, custom_filename=None):
        """Download file from URL to local disk supporting resume and tqdm progress bar."""
        # Check if output_path is an existing directory, or ends with path separator, or custom_filename is given
        if os.path.isdir(output_path) or output_path.endswith(os.sep) or output_path.endswith("/") or custom_filename:
            dir_path = output_path
            os.makedirs(dir_path, exist_ok=True)
            if not custom_filename:
                custom_filename = os.path.basename(url.split("?")[0]) or "downloaded_file"
            filepath = os.path.join(dir_path, custom_filename)
        else:
            filepath = output_path
            dir_path = os.path.dirname(os.path.abspath(filepath))
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

        existing_file_size = 0
        if os.path.exists(filepath):
            existing_file_size = os.path.getsize(filepath)

        headers = {}
        if existing_file_size > 0:
            headers["Range"] = f"bytes={existing_file_size}-"

        response = self.session.get(url, headers=headers, stream=True, timeout=30)

        # Handle range response (206) or full file response (200)
        if response.status_code == 206:
            mode = "ab"
            content_range = response.headers.get("Content-Range", "")
            if "/" in content_range:
                total_size = int(content_range.split("/")[-1])
            else:
                total_size = existing_file_size + int(response.headers.get("Content-Length", 0))
        elif response.status_code == 200:
            mode = "wb"
            existing_file_size = 0
            total_size = int(response.headers.get("Content-Length", 0))
        else:
            raise RuntimeError(f"Download failed with status code {response.status_code}")

        if existing_file_size >= total_size and total_size > 0:
            print(f"File '{filepath}' is already fully downloaded ({existing_file_size} bytes).")
            return filepath

        with open(filepath, mode) as f:
            with tqdm(
                total=total_size,
                initial=existing_file_size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=os.path.basename(filepath),
                ascii=True
            ) as pbar:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        return filepath
