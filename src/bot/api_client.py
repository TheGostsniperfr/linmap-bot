import httpx
import logging
from typing import Optional
from src.config import settings

logger = logging.getLogger(__name__)

class LinmapAPIClient:
    """Async client helper used by the Discord Bot to interact with the FastAPI backend."""
    
    def __init__(self) -> None:
        self.base_url = f"{settings.API_INTERNAL_URL}/api/v1"

    async def trigger_generation(self, months: Optional[int] = None) -> dict:
        """Triggers the pipeline with an optional months zoom parameter."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            params = {}
            if months is not None:
                params["months"] = months 
                
            try:
                response = await client.post(f"{self.base_url}/roadmap/generate", params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to communicate with Linmap API: {e}")
                raise RuntimeError("API unreachable or returned an error.") from e

    async def fetch_gantt_image(self) -> Optional[bytes]:
        """Downloads the Gantt chart binary stream from the API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{self.base_url}/roadmap/image")
                response.raise_for_status()
                return response.content
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch Gantt chart image binary: {e}")
                return None

    async def fetch_excel_file(self) -> Optional[bytes]:
            """Downloads the Excel report binary stream from the API."""
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.get(f"{self.base_url}/roadmap/excel")
                    response.raise_for_status()
                    return response.content
                except httpx.HTTPError as e:
                    logger.error(f"Failed to fetch Excel binary: {e}")
                    return None