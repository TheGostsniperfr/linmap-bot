import os
import logging
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from src.config import settings
from src.storage.base import BaseStorage

logger = logging.getLogger(__name__)

class GoogleDriveStorage(BaseStorage):
    """
    Google Drive storage implementation. Handles authenticated uploads,
    file overwrites (idempotency), and public sharing permission policies.
    """
    
    def __init__(self) -> None:
        self.scopes = ["https://www.googleapis.com/auth/drive"]
        self.service = self._authenticate()

    def _authenticate(self):
        """Authenticates using Service Account JSON file path or JSON content directly."""
        creds_content = settings.GOOGLE_APPLICATION_CREDENTIALS
        if not creds_content:
            logger.error("Google credentials are not set (GOOGLE_APPLICATION_CREDENTIALS is empty).")
            raise ValueError("Google credentials are not set.")

        # Check if credentials are provided directly as a JSON string
        if creds_content.strip().startswith("{"):
            try:
                import json
                info = json.loads(creds_content)
                creds = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=self.scopes
                )
                return build("drive", "v3", credentials=creds)
            except Exception as e:
                logger.error(f"Failed to load Google credentials from JSON string: {e}")
                raise RuntimeError("Google Drive authentication from JSON string failed.") from e

        # Fallback to loading from file
        if not os.path.exists(creds_content):
            logger.error(f"Google credentials file not found at: {creds_content}")
            raise FileNotFoundError(f"Missing Google credentials file at {creds_content}")
            
        try:
            creds = service_account.Credentials.from_service_account_file(
                creds_content, 
                scopes=self.scopes
            )
            return build("drive", "v3", credentials=creds)
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive client from file: {e}")
            raise RuntimeError("Google Drive authentication from file failed.") from e

    def _find_existing_file_id(self, filename: str, folder_id: str) -> Optional[str]:
        """Queries Google Drive for an existing active file with the same name within the folder."""
        query = (
            f"name = '{filename}' and "
            f"'{folder_id}' in parents and "
            f"trashed = false"
        )
        try:
            response = self.service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                pageSize=1 
            ).execute()
            files = response.get("files", [])
            return files[0]["id"] if files else None
        except HttpError as e:
            logger.error(f"Error querying existing file from Google Drive: {e}")
            return None

    def _set_public_permissions(self, file_id: str) -> None:
        """Sets file permission to public-read (anyone with the link can view)."""
        user_permission = {
            "type": "anyone",
            "role": "reader"
        }
        try:
            self.service.permissions().create(
                fileId=file_id,
                body=user_permission,
                fields="id"
            ).execute()
        except HttpError as e:
            logger.error(f"Failed to set sharing permissions on file {file_id}: {e}")
            raise

    def upload_file(self, local_file_path: str, remote_filename: str) -> str:
        """
        Uploads or updates a file in the configured Google Drive folder.
        Guarantees a static shareable webViewLink.
        """
        if not os.path.exists(local_file_path):
            logger.error(f"Local file does not exist: {local_file_path}")
            raise FileNotFoundError(f"Local file not found: {local_file_path}")

        folder_id = settings.GDRIVE_FOLDER_ID
        existing_file_id = self._find_existing_file_id(remote_filename, folder_id)
        
        # Deduce mime type (basic fallback for report visual/table)
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if local_file_path.endswith(".png"):
            mime_type = "image/png"

        media = MediaFileUpload(local_file_path, mimetype=mime_type, resumable=True)

        try:
            if existing_file_id:
                logger.info(f"Existing file found (ID: {existing_file_id}). Updating media...")
                file = self.service.files().update(
                    fileId=existing_file_id,
                    media_body=media,
                    fields="id, webViewLink"
                ).execute()
                file_id = existing_file_id
            else:
                logger.info(f"No existing file found. Creating new file '{remote_filename}'...")
                file_metadata = {
                    "name": remote_filename,
                    "parents": [folder_id]
                }
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields="id, webViewLink"
                ).execute()
                file_id = file.get("id")

            # Ensure the file is shared publicly
            self._set_public_permissions(file_id)

            # Re-fetch metadata with permission update security
            file_metadata = self.service.files().get(
                fileId=file_id, 
                fields="webViewLink"
            ).execute()
            
            web_link = file_metadata.get("webViewLink")
            logger.info(f"File sync complete. Shared link: {web_link}")
            return web_link

        except HttpError as e:
            logger.error(f"Google Drive API transaction failed: {e}")
            raise RuntimeError(f"Drive API failed: {e.content}") from e
