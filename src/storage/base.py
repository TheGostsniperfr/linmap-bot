from abc import ABC, abstractmethod

class BaseStorage(ABC):
    """Abstract base class representing a storage backend."""

    @abstractmethod
    def upload_file(self, local_file_path: str, remote_filename: str) -> str:
        """
        Uploads a file to the storage backend.
        
        Args:
            local_file_path: Path to the local file to upload.
            remote_filename: Target filename in the remote storage.
            
        Returns:
            str: The unified shareable URL/link to the uploaded file.
        """
        pass
