import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.api.app import app
from src.bot.api_client import LinmapAPIClient
import httpx

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy", "version": "1.0.0"})

    @patch("src.api.routers.roadmap.LinearClient")
    @patch("src.api.routers.roadmap.generate_excel_report")
    @patch("src.api.routers.roadmap.generate_gantt_chart")
    @patch("src.api.routers.roadmap.GoogleDriveStorage")
    def test_generate_roadmap_endpoint(self, mock_gdrive_storage_cls, mock_gantt, mock_excel, mock_linear_client_cls):
        # Mock Linear Client
        mock_client = MagicMock()
        mock_client.fetch_roadmap_data.return_value = {
            "projects": {
                "nodes": [
                    {
                        "name": "Test Project",
                        "startDate": "2026-05-31",
                        "targetDate": "2026-07-13",
                        "state": "started",
                        "milestones": {"nodes": []},
                        "issues": {"nodes": []}
                    }
                ]
            }
        }
        mock_linear_client_cls.return_value = mock_client

        # Mock Google Drive Storage
        mock_storage = MagicMock()
        mock_storage.upload_file.return_value = "https://drive.google.com/file/d/mock-id/view"
        mock_gdrive_storage_cls.return_value = mock_storage

        response = self.client.post("/api/v1/roadmap/generate")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["excel_url"], "https://drive.google.com/file/d/mock-id/view")
        self.assertIn("gantt_image_path", data)
        
        mock_excel.assert_called_once()
        mock_gantt.assert_called_once()
        mock_gdrive_storage_cls.assert_called_once()
        mock_storage.upload_file.assert_called_once_with("/tmp/roadmap.xlsx", "Linear_Roadmap.xlsx")

    def test_get_gantt_image_success(self):
        # Create a dummy image file
        with open("/tmp/roadmap.png", "wb") as f:
            f.write(b"dummy_png_bytes")
            
        try:
            response = self.client.get("/api/v1/roadmap/image")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"dummy_png_bytes")
            self.assertEqual(response.headers["content-type"], "image/png")
        finally:
            if os.path.exists("/tmp/roadmap.png"):
                os.remove("/tmp/roadmap.png")

    @patch("src.api.routers.roadmap.os.path.exists")
    def test_get_gantt_image_not_found(self, mock_exists):
        mock_exists.return_value = False
        
        response = self.client.get("/api/v1/roadmap/image")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Gantt chart image not found. Generate it first.")

    def test_get_excel_file_success(self):
        # Create a dummy excel file
        with open("/tmp/roadmap.xlsx", "wb") as f:
            f.write(b"dummy_xlsx_bytes")
            
        try:
            response = self.client.get("/api/v1/roadmap/excel")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"dummy_xlsx_bytes")
            self.assertEqual(
                response.headers["content-type"], 
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        finally:
            if os.path.exists("/tmp/roadmap.xlsx"):
                os.remove("/tmp/roadmap.xlsx")

    @patch("src.api.routers.roadmap.os.path.exists")
    def test_get_excel_file_not_found(self, mock_exists):
        mock_exists.return_value = False
        
        response = self.client.get("/api/v1/roadmap/excel")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Excel report not found. Generate it first.")


class TestBotAPIClient(unittest.IsolatedAsyncioTestCase):
    @patch("src.bot.api_client.httpx.AsyncClient.post")
    async def test_trigger_generation_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "message": "Roadmap successfully synchronized.",
            "excel_url": "https://drive.google.com/file/d/mock-id/view",
            "gantt_image_path": "/tmp/roadmap.png"
        }
        mock_post.return_value = mock_response

        client = LinmapAPIClient()
        res = await client.trigger_generation()
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["excel_url"], "https://drive.google.com/file/d/mock-id/view")

    @patch("src.bot.api_client.httpx.AsyncClient.post")
    async def test_trigger_generation_http_error(self, mock_post):
        mock_post.side_effect = httpx.HTTPError("Connection failed")
        client = LinmapAPIClient()
        
        with self.assertRaises(RuntimeError) as context:
            await client.trigger_generation()
            
        self.assertIn("API unreachable", str(context.exception))
