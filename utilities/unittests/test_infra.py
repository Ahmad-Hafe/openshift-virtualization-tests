# Generated using Claude cli

"""Unit tests for infra module - download_and_extract_file_from_cluster"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

import utilities

mock_virt = MagicMock()
sys.modules["utilities.virt"] = mock_virt
utilities.virt = mock_virt

if "utilities.infra" in sys.modules:
    del sys.modules["utilities.infra"]

from utilities.infra import download_and_extract_file_from_cluster


class TestDownloadAndExtractFileFromCluster:
    """Test cases for download_and_extract_file_from_cluster function"""

    @pytest.fixture
    def mock_tmpdir(self, tmp_path):
        """Mock tmpdir with py.path.local-like interface"""
        tmpdir = MagicMock()
        tmpdir.__str__ = lambda self: str(tmp_path)
        tmpdir.__fspath__ = lambda self: str(tmp_path)
        tmpdir.strpath = str(tmp_path)
        return tmpdir

    @pytest.fixture
    def mock_response(self):
        """Mock successful HTTP response"""
        response = MagicMock()
        response.content = b"fake archive content"
        response.raise_for_status = MagicMock()
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        return response

    @patch("utilities.infra.tarfile.open")
    @patch("utilities.infra.os.remove")
    @patch("utilities.infra.os.path.isfile", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    @patch("utilities.infra.TimeoutSampler")
    @patch("utilities.infra.urllib3.disable_warnings")
    def test_successful_tar_download(
        self,
        mock_disable_warnings,
        mock_sampler,
        mocked_open,
        mock_isfile,
        mock_remove,
        mock_tarfile,
        mock_tmpdir,
        mock_response,
    ):
        """Test successful download and extraction of a tar file"""
        mock_sampler.return_value = iter([mock_response])
        mock_archive = MagicMock()
        mock_archive.getnames.return_value = ["virtctl"]
        mock_tarfile.return_value = mock_archive

        url = "https://cluster.example.com/downloads/virtctl.tar.gz"
        result = download_and_extract_file_from_cluster(tmpdir=mock_tmpdir, url=url)

        mock_sampler.assert_called_once()
        call_kwargs = mock_sampler.call_args[1]
        assert call_kwargs["func"] == requests.get
        assert call_kwargs["url"] == url
        assert call_kwargs["verify"] is False
        assert call_kwargs["timeout"] == 30
        assert requests.exceptions.SSLError in call_kwargs["exceptions_dict"]
        assert requests.exceptions.ConnectionError in call_kwargs["exceptions_dict"]
        assert requests.exceptions.Timeout in call_kwargs["exceptions_dict"]

        mock_response.raise_for_status.assert_called_once()
        mock_archive.extractall.assert_called_once_with(path=mock_tmpdir)
        assert result == [f"{mock_tmpdir.strpath}/virtctl"]

    @patch("utilities.infra.zipfile.ZipFile")
    @patch("utilities.infra.os.remove")
    @patch("utilities.infra.os.path.isfile", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    @patch("utilities.infra.TimeoutSampler")
    @patch("utilities.infra.urllib3.disable_warnings")
    def test_successful_zip_download(
        self,
        mock_disable_warnings,
        mock_sampler,
        mocked_open,
        mock_isfile,
        mock_remove,
        mock_zipfile,
        mock_tmpdir,
        mock_response,
    ):
        """Test successful download and extraction of a zip file"""
        mock_sampler.return_value = iter([mock_response])
        mock_archive = MagicMock()
        mock_archive.namelist.return_value = ["virtctl.exe"]
        mock_zipfile.return_value = mock_archive

        url = "https://cluster.example.com/downloads/virtctl.zip"
        result = download_and_extract_file_from_cluster(tmpdir=mock_tmpdir, url=url)

        mock_zipfile.assert_called_once()
        mock_archive.extractall.assert_called_once_with(path=mock_tmpdir)
        assert result == [f"{mock_tmpdir.strpath}/virtctl.exe"]

    @patch("utilities.infra.tarfile.open")
    @patch("utilities.infra.os.remove")
    @patch("utilities.infra.os.path.isfile", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    @patch("utilities.infra.TimeoutSampler")
    @patch("utilities.infra.urllib3.disable_warnings")
    def test_file_cleaned_up_after_extraction(
        self,
        mock_disable_warnings,
        mock_sampler,
        mocked_open,
        mock_isfile,
        mock_remove,
        mock_tarfile,
        mock_tmpdir,
        mock_response,
    ):
        """Test that the downloaded archive file is removed after extraction"""
        mock_sampler.return_value = iter([mock_response])
        mock_archive = MagicMock()
        mock_archive.getnames.return_value = ["virtctl"]
        mock_tarfile.return_value = mock_archive

        url = "https://cluster.example.com/downloads/virtctl.tar.gz"
        download_and_extract_file_from_cluster(tmpdir=mock_tmpdir, url=url)

        mock_remove.assert_called_once()

    @patch("utilities.infra.tarfile.open")
    @patch("utilities.infra.os.remove")
    @patch("utilities.infra.os.path.isfile", return_value=False)
    @patch("builtins.open", new_callable=mock_open)
    @patch("utilities.infra.TimeoutSampler")
    @patch("utilities.infra.urllib3.disable_warnings")
    def test_file_not_removed_if_not_exists(
        self,
        mock_disable_warnings,
        mock_sampler,
        mocked_open,
        mock_isfile,
        mock_remove,
        mock_tarfile,
        mock_tmpdir,
        mock_response,
    ):
        """Test that os.remove is not called if file doesn't exist"""
        mock_sampler.return_value = iter([mock_response])
        mock_archive = MagicMock()
        mock_archive.getnames.return_value = ["virtctl"]
        mock_tarfile.return_value = mock_archive

        url = "https://cluster.example.com/downloads/virtctl.tar.gz"
        download_and_extract_file_from_cluster(tmpdir=mock_tmpdir, url=url)

        mock_remove.assert_not_called()

    @patch("utilities.infra.tarfile.open")
    @patch("utilities.infra.os.remove")
    @patch("utilities.infra.os.path.isfile", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    @patch("utilities.infra.TimeoutSampler")
    @patch("utilities.infra.urllib3.disable_warnings")
    def test_multiple_extracted_files(
        self,
        mock_disable_warnings,
        mock_sampler,
        mocked_open,
        mock_isfile,
        mock_remove,
        mock_tarfile,
        mock_tmpdir,
        mock_response,
    ):
        """Test extraction with multiple files in archive"""
        mock_sampler.return_value = iter([mock_response])
        mock_archive = MagicMock()
        mock_archive.getnames.return_value = ["virtctl", "LICENSE", "README.md"]
        mock_tarfile.return_value = mock_archive

        url = "https://cluster.example.com/downloads/virtctl.tar.gz"
        result = download_and_extract_file_from_cluster(tmpdir=mock_tmpdir, url=url)

        assert len(result) == 3
        assert f"{mock_tmpdir.strpath}/virtctl" in result
        assert f"{mock_tmpdir.strpath}/LICENSE" in result
        assert f"{mock_tmpdir.strpath}/README.md" in result

    @patch("utilities.infra.TimeoutSampler")
    @patch("utilities.infra.urllib3.disable_warnings")
    def test_retry_on_ssl_error(self, mock_disable_warnings, mock_sampler, mock_tmpdir):
        """Test that SSLError is configured for retry in TimeoutSampler"""
        mock_sampler.side_effect = requests.exceptions.SSLError("EOF occurred in violation of protocol")

        url = "https://cluster.example.com/downloads/virtctl.tar.gz"
        with pytest.raises(requests.exceptions.SSLError):
            download_and_extract_file_from_cluster(tmpdir=mock_tmpdir, url=url)

        call_kwargs = mock_sampler.call_args[1]
        assert requests.exceptions.SSLError in call_kwargs["exceptions_dict"]

    @patch("utilities.infra.TimeoutSampler")
    @patch("utilities.infra.urllib3.disable_warnings")
    def test_retry_on_connection_error(self, mock_disable_warnings, mock_sampler, mock_tmpdir):
        """Test that ConnectionError is configured for retry in TimeoutSampler"""
        mock_sampler.side_effect = requests.exceptions.ConnectionError("Connection reset")

        url = "https://cluster.example.com/downloads/virtctl.tar.gz"
        with pytest.raises(requests.exceptions.ConnectionError):
            download_and_extract_file_from_cluster(tmpdir=mock_tmpdir, url=url)

        call_kwargs = mock_sampler.call_args[1]
        assert requests.exceptions.ConnectionError in call_kwargs["exceptions_dict"]

    @patch("utilities.infra.TimeoutSampler")
    @patch("utilities.infra.urllib3.disable_warnings")
    def test_retry_on_timeout(self, mock_disable_warnings, mock_sampler, mock_tmpdir):
        """Test that Timeout is configured for retry in TimeoutSampler"""
        mock_sampler.side_effect = requests.exceptions.Timeout("Request timed out")

        url = "https://cluster.example.com/downloads/virtctl.tar.gz"
        with pytest.raises(requests.exceptions.Timeout):
            download_and_extract_file_from_cluster(tmpdir=mock_tmpdir, url=url)

        call_kwargs = mock_sampler.call_args[1]
        assert requests.exceptions.Timeout in call_kwargs["exceptions_dict"]

    @patch("utilities.infra.tarfile.open")
    @patch("utilities.infra.os.remove")
    @patch("utilities.infra.os.path.isfile", return_value=True)
    @patch("utilities.infra.TimeoutSampler")
    @patch("utilities.infra.urllib3.disable_warnings")
    def test_response_content_written_to_file(
        self, mock_disable_warnings, mock_sampler, mock_isfile, mock_remove, mock_tarfile, mock_tmpdir, mock_response
    ):
        """Test that response content is written to file correctly"""
        mock_response.content = b"binary archive data"
        mock_sampler.return_value = iter([mock_response])
        mock_archive = MagicMock()
        mock_archive.getnames.return_value = ["virtctl"]
        mock_tarfile.return_value = mock_archive

        url = "https://cluster.example.com/downloads/virtctl.tar.gz"
        with patch("builtins.open", mock_open()) as mocked_file:
            download_and_extract_file_from_cluster(tmpdir=mock_tmpdir, url=url)
            mocked_file().write.assert_called_once_with(b"binary archive data")
