import json
import os
import requests

DEFAULT_CLIENT_ID = "OKC1fA302685934149"
USER_API_HOST = "https://user.mypikpak.com"
DRIVE_API_HOST = "https://api-drive.mypikpak.com"
CONFIG_PATH = os.path.expanduser("~/.pikpak_credentials.json")


class PikPakError(Exception):
    """Custom exception for PikPak API errors."""
    pass


class PikPakClient:
    """Client for interacting with PikPak Drive API."""

    def __init__(self, username=None, password=None, client_id=DEFAULT_CLIENT_ID):
        self.client_id = client_id
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PikPakDownloader/1.0",
            "Content-Type": "application/json; charset=utf-8"
        })

    def load_credentials(self, filepath=CONFIG_PATH):
        """Load cached tokens/credentials from a JSON file."""
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.access_token = data.get("access_token")
                    self.refresh_token = data.get("refresh_token")
                    self.user_id = data.get("user_id")
                    self.username = data.get("username", self.username)
                    return True
            except Exception:
                return False
        return False

    def save_credentials(self, filepath=CONFIG_PATH):
        """Save tokens/credentials to a JSON file."""
        data = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "user_id": self.user_id,
            "username": self.username
        }
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def login(self, username=None, password=None):
        """Authenticate user with username/email and password."""
        if username:
            self.username = username
        if password:
            self.password = password

        if not self.username or not self.password:
            raise PikPakError("Username and password are required for login.")

        url = f"{USER_API_HOST}/v1/auth/signin"
        payload = {
            "client_id": self.client_id,
            "username": self.username,
            "password": self.password
        }

        response = self.session.post(url, json=payload)
        data = response.json()

        if response.status_code != 200 or "access_token" not in data:
            error_msg = data.get("error_description") or data.get("message") or str(data)
            raise PikPakError(f"Login failed ({response.status_code}): {error_msg}")

        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token")
        self.user_id = data.get("sub")
        self.save_credentials()
        return data

    def refresh_access_token(self):
        """Refresh access token using stored refresh token."""
        if not self.refresh_token:
            raise PikPakError("No refresh token available.")

        url = f"{USER_API_HOST}/v1/auth/token"
        payload = {
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }

        response = self.session.post(url, json=payload)
        data = response.json()

        if response.status_code != 200 or "access_token" not in data:
            error_msg = data.get("error_description") or data.get("message") or str(data)
            raise PikPakError(f"Token refresh failed ({response.status_code}): {error_msg}")

        self.access_token = data["access_token"]
        if "refresh_token" in data:
            self.refresh_token = data["refresh_token"]
        self.save_credentials()
        return data

    def _get_headers(self):
        """Get request headers including authorization Bearer token."""
        if not self.access_token:
            if not self.load_credentials() or not self.access_token:
                raise PikPakError("Not authenticated. Please login first.")
        return {
            "Authorization": f"Bearer {self.access_token}"
        }

    def list_files(self, parent_id="", limit=100, page_token=""):
        """List files and folders in a specified parent folder."""
        url = f"{DRIVE_API_HOST}/drive/v1/files"
        params = {
            "limit": limit,
            "filters": json.dumps({"trashed": {"eq": False}})
        }
        if parent_id:
            params["parent_id"] = parent_id
        if page_token:
            params["page_token"] = page_token

        headers = self._get_headers()
        response = self.session.get(url, headers=headers, params=params)
        data = response.json()

        if response.status_code == 401 and self.refresh_token:
            self.refresh_access_token()
            headers = self._get_headers()
            response = self.session.get(url, headers=headers, params=params)
            data = response.json()

        if response.status_code != 200:
            raise PikPakError(f"Failed to list files ({response.status_code}): {data}")

        return data

    def get_file_info(self, file_id):
        """Get details for a single file or folder."""
        url = f"{DRIVE_API_HOST}/drive/v1/files/{file_id}"
        headers = self._get_headers()
        response = self.session.get(url, headers=headers)
        data = response.json()

        if response.status_code == 401 and self.refresh_token:
            self.refresh_access_token()
            headers = self._get_headers()
            response = self.session.get(url, headers=headers)
            data = response.json()

        if response.status_code != 200:
            raise PikPakError(f"Failed to get file info ({response.status_code}): {data}")

        return data

    def get_download_url(self, file_id):
        """Retrieve direct web download URL for a file."""
        file_info = self.get_file_info(file_id)
        web_content_link = file_info.get("web_content_link")
        if web_content_link:
            return web_content_link

        # Fallback to links list if available
        links = file_info.get("links", {})
        if isinstance(links, dict) and links:
            first_link = list(links.values())[0]
            if isinstance(first_link, dict) and "url" in first_link:
                return first_link["url"]
            elif isinstance(first_link, str):
                return first_link

        raise PikPakError(f"No direct download URL found for file_id {file_id}")

    def add_file_url(self, url, parent_id="", name=""):
        """Add an offline task or URL (magnet, torrent, HTTP) to PikPak drive."""
        api_url = f"{DRIVE_API_HOST}/drive/v1/files"
        payload = {
            "kind": "drive#file",
            "upload_type": "UPLOAD_TYPE_URL",
            "url": {"url": url},
            "folder_type": "DOWNLOAD"
        }
        if name:
            payload["name"] = name
        if parent_id:
            payload["parent_id"] = parent_id

        headers = self._get_headers()
        response = self.session.post(api_url, headers=headers, json=payload)
        data = response.json()

        if response.status_code == 401 and self.refresh_token:
            self.refresh_access_token()
            headers = self._get_headers()
            response = self.session.post(api_url, headers=headers, json=payload)
            data = response.json()

        if response.status_code not in (200, 201):
            raise PikPakError(f"Failed to add URL task ({response.status_code}): {data}")

        return data

    def get_task(self, task_id):
        """Get status of an offline task."""
        url = f"{DRIVE_API_HOST}/drive/v1/tasks/{task_id}"
        headers = self._get_headers()
        response = self.session.get(url, headers=headers)
        data = response.json()

        if response.status_code == 401 and self.refresh_token:
            self.refresh_access_token()
            headers = self._get_headers()
            response = self.session.get(url, headers=headers)
            data = response.json()

        if response.status_code != 200:
            raise PikPakError(f"Failed to get task status ({response.status_code}): {data}")

        return data
