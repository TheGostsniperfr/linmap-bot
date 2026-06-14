import unittest
from unittest.mock import patch, MagicMock
from googleapiclient.errors import HttpError
from src.storage.gdrive import GoogleDriveStorage

class TestGoogleDriveStorage(unittest.TestCase):
    
    @patch("src.storage.gdrive.settings")
    @patch("src.storage.gdrive.build")
    @patch("src.storage.gdrive.service_account.Credentials.from_service_account_file")
    @patch("src.storage.gdrive.os.path.exists")
    def setUp(self, mock_exists, mock_from_file, mock_build, mock_settings):
        # Configure settings mock
        mock_settings.GOOGLE_APPLICATION_CREDENTIALS = "/dummy/credentials.json"
        mock_settings.GDRIVE_FOLDER_ID = "mock_folder_id"
        
        # Make credentials file exist
        mock_exists.return_value = True
        
        # Configure credentials mock
        self.mock_creds = MagicMock()
        mock_from_file.return_value = self.mock_creds
        
        # Configure service builder mock
        self.mock_service = MagicMock()
        mock_build.return_value = self.mock_service
        
        # Initialize storage
        self.storage = GoogleDriveStorage()
        
    @patch("src.storage.gdrive.os.path.exists")
    @patch("src.storage.gdrive.MediaFileUpload")
    def test_upload_file_new(self, mock_media_upload_cls, mock_exists):
        # Local file must exist
        mock_exists.return_value = True
        
        # Mock file search returning empty
        self.mock_service.files().list.return_value.execute.return_value = {"files": []}
        
        # Mock file creation
        mock_created_file = {"id": "new_file_id", "webViewLink": "https://drive.google.com/file/d/new_file_id/view"}
        self.mock_service.files().create.return_value.execute.return_value = mock_created_file
        
        # Mock setting permissions
        self.mock_service.permissions().create.return_value.execute.return_value = {"id": "permission_id"}
        
        # Mock refetch metadata
        self.mock_service.files().get.return_value.execute.return_value = {"webViewLink": "https://drive.google.com/file/d/new_file_id/view"}
        
        link = self.storage.upload_file("/dummy/local_file.xlsx", "Linear_Roadmap.xlsx")
        
        self.assertEqual(link, "https://drive.google.com/file/d/new_file_id/view")
        self.mock_service.files().list.assert_called_once()
        self.mock_service.files().create.assert_called_once()
        self.mock_service.permissions().create.assert_called_once()
        self.mock_service.files().get.assert_called_once_with(fileId="new_file_id", fields="webViewLink")
        
    @patch("src.storage.gdrive.os.path.exists")
    @patch("src.storage.gdrive.MediaFileUpload")
    def test_upload_file_overwrite(self, mock_media_upload_cls, mock_exists):
        # Local file must exist
        mock_exists.return_value = True
        
        # Mock file search returning existing file ID
        self.mock_service.files().list.return_value.execute.return_value = {"files": [{"id": "existing_file_id", "name": "Linear_Roadmap.xlsx"}]}
        
        # Mock file update
        mock_updated_file = {"id": "existing_file_id", "webViewLink": "https://drive.google.com/file/d/existing_file_id/view"}
        self.mock_service.files().update.return_value.execute.return_value = mock_updated_file
        
        # Mock setting permissions
        self.mock_service.permissions().create.return_value.execute.return_value = {"id": "permission_id"}
        
        # Mock refetch metadata
        self.mock_service.files().get.return_value.execute.return_value = {"webViewLink": "https://drive.google.com/file/d/existing_file_id/view"}
        
        link = self.storage.upload_file("/dummy/local_file.xlsx", "Linear_Roadmap.xlsx")
        
        self.assertEqual(link, "https://drive.google.com/file/d/existing_file_id/view")
        self.mock_service.files().list.assert_called_once()
        self.mock_service.files().update.assert_called_once()
        self.mock_service.permissions().create.assert_called_once()
        self.mock_service.files().get.assert_called_once_with(fileId="existing_file_id", fields="webViewLink")

    @patch("src.storage.gdrive.os.path.exists")
    def test_upload_file_not_found(self, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(FileNotFoundError):
            self.storage.upload_file("/dummy/missing_file.xlsx", "Linear_Roadmap.xlsx")
