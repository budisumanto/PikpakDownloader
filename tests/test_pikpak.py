import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from pikpak_client import PikPakClient, PikPakError
from downloader import Downloader


class MockResponse:
    def __init__(self, json_data, status_code=200, headers=None, content=b""):
        self._json_data = json_data
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content

    def json(self):
        return self._json_data

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]


def test_pikpak_login_success(tmp_path):
    cred_file = os.path.join(tmp_path, "creds.json")
    client = PikPakClient(username="testuser", password="testpassword")

    mock_resp = MockResponse({
        "access_token": "mock_access_token_123",
        "refresh_token": "mock_refresh_token_456",
        "sub": "user_12345"
    })

    with patch.object(client.session, 'post', return_value=mock_resp):
        res = client.login()
        assert res["access_token"] == "mock_access_token_123"
        assert client.access_token == "mock_access_token_123"
        assert client.refresh_token == "mock_refresh_token_456"


def test_pikpak_login_failure():
    client = PikPakClient(username="user", password="wrongpassword")
    mock_resp = MockResponse({"error_description": "Invalid password"}, status_code=400)

    with patch.object(client.session, 'post', return_value=mock_resp):
        with pytest.raises(PikPakError) as exc_info:
            client.login()
        assert "Login failed" in str(exc_info.value)


def test_pikpak_list_files():
    client = PikPakClient()
    client.access_token = "valid_token"

    mock_resp = MockResponse({
        "files": [
            {"id": "file1", "name": "movie.mp4", "kind": "drive#file", "size": "1048576"},
            {"id": "folder1", "name": "Videos", "kind": "drive#folder", "size": "0"}
        ]
    })

    with patch.object(client.session, 'get', return_value=mock_resp):
        res = client.list_files()
        assert len(res["files"]) == 2
        assert res["files"][0]["name"] == "movie.mp4"


def test_pikpak_add_file_url():
    client = PikPakClient()
    client.access_token = "valid_token"

    mock_resp = MockResponse({
        "task": {"id": "task_999", "name": "sample.torrent"}
    }, status_code=200)

    with patch.object(client.session, 'post', return_value=mock_resp):
        res = client.add_file_url("magnet:?xt=urn:btih:1234567890abcdef")
        assert res["task"]["id"] == "task_999"


def test_downloader_chunked_download(tmp_path):
    downloader = Downloader(chunk_size=10)
    out_file = tmp_path / "test_download.bin"

    file_content = b"Hello, PikPak Downloader! " * 50
    mock_resp = MockResponse(
        json_data={},
        status_code=200,
        headers={"Content-Length": str(len(file_content))},
        content=file_content
    )

    with patch.object(downloader.session, 'get', return_value=mock_resp):
        result_path = downloader.download_file("https://example.com/file.bin", str(out_file))
        assert os.path.exists(result_path)
        with open(result_path, "rb") as f:
            data = f.read()
        assert data == file_content


def test_downloader_resume(tmp_path):
    downloader = Downloader(chunk_size=10)
    out_file = tmp_path / "test_resume.bin"

    initial_content = b"Hello, "
    remaining_content = b"PikPak Downloader!"

    with open(out_file, "wb") as f:
        f.write(initial_content)

    mock_resp = MockResponse(
        json_data={},
        status_code=206,
        headers={
            "Content-Range": f"bytes 7-24/{len(initial_content) + len(remaining_content)}"
        },
        content=remaining_content
    )

    with patch.object(downloader.session, 'get', return_value=mock_resp):
        result_path = downloader.download_file("https://example.com/file.bin", str(out_file))
        assert os.path.exists(result_path)
        with open(result_path, "rb") as f:
            data = f.read()
        assert data == initial_content + remaining_content
