import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.linear.graphql_client import LinearClient
from src.generator.excel import generate_excel_report
from src.generator.timeline import generate_gantt_chart
from src.storage.gdrive import GoogleDriveStorage
from src.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/roadmap", tags=["Roadmap Generation"])

GANTT_OUTPUT_PATH = "/tmp/roadmap.png"
EXCEL_OUTPUT_PATH = "/tmp/roadmap.xlsx"

class RoadmapResponse(BaseModel):
    status: str
    message: str
    excel_url: str
    gantt_image_path: str

@router.post("/generate", response_model=RoadmapResponse)
async def generate_roadmap(months: Optional[int] = None):
    """
    Core pipeline execution:
    1. Fetch data from Linear.
    2. Generate formatted Excel workbook.
    3. Render Gantt chart image with Plotly & save locally (with optional temporal zoom).
    4. Upload Excel file to Google Drive (optional fallback).
    5. Return URLs and file references.
    """
    try:
        # 1. Fetch Linear Data
        logger.info("Initializing LinearClient and fetching data...")
        client = LinearClient()
        roadmap_data = client.fetch_roadmap_data()
        
        # 2. Run Excel Generator
        logger.info("Running Excel generation engine...")
        generate_excel_report(roadmap_data, EXCEL_OUTPUT_PATH)
        
        # 3. Run Gantt Renderer (supporting optional temporal zoom parameter)
        logger.info(f"Running Gantt rendering engine (Zoom: {months} months)...")
        generate_gantt_chart(roadmap_data, GANTT_OUTPUT_PATH, months_zoom=months)
        
        # 4. Upload via Storage (Failsafe & Optional Fallback)
        excel_url = "Attached to Discord message"
        try:
            # Only attempt GDrive upload if credentials are configured and folder ID isn't the default placeholder
            creds = settings.GOOGLE_APPLICATION_CREDENTIALS
            is_creds_configured = False
            if creds:
                if creds.strip().startswith("{"):
                    is_creds_configured = True
                elif os.path.exists(creds):
                    is_creds_configured = True

            if is_creds_configured and settings.GDRIVE_FOLDER_ID != "gdrive_folder_alphanumeric_id":
                logger.info("Initializing GoogleDriveStorage and uploading report...")
                storage = GoogleDriveStorage()
                excel_url = storage.upload_file(EXCEL_OUTPUT_PATH, "Linear_Roadmap.xlsx")
            else:
                logger.info("Google Drive credentials not configured. Skipping Drive upload step.")
        except Exception as upload_err:
            logger.warning(
                f"Google Drive upload bypassed due to quota/permission limits: {upload_err}. "
                "The spreadsheet will be attached directly to the Discord message instead."
            )
        
        return RoadmapResponse(
            status="success",
            message="Roadmap successfully synchronized.",
            excel_url=excel_url,
            gantt_image_path=GANTT_OUTPUT_PATH
        )
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/image", response_class=FileResponse)
async def get_gantt_image():
    """Serves the latest rendered Gantt chart image."""
    if not os.path.exists(GANTT_OUTPUT_PATH):
        raise HTTPException(status_code=404, detail="Gantt chart image not found. Generate it first.")
    return FileResponse(GANTT_OUTPUT_PATH, media_type="image/png", filename="roadmap.png")

@router.get("/excel", response_class=FileResponse)
async def get_excel_file():
    """Serves the latest rendered Excel spreadsheet."""
    if not os.path.exists(EXCEL_OUTPUT_PATH):
        raise HTTPException(status_code=404, detail="Excel report not found. Generate it first.")
    return FileResponse(
        EXCEL_OUTPUT_PATH, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        filename="Linear_Roadmap.xlsx"
    )