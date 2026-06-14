import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
import discord
from src.bot.api_client import LinmapAPIClient
from src.bot.discord_client import LinmapBot

class TestLinmapBot(unittest.IsolatedAsyncioTestCase):
    
    @patch("src.bot.discord_client.LinmapAPIClient")
    async def test_bot_run_pipeline_and_post_success(self, mock_client_cls):
        # Setup mocks
        mock_client = MagicMock()
        mock_client.trigger_generation = AsyncMock(return_value={
            "status": "success",
            "excel_url": "https://drive.google.com/file/d/mock-id/view",
            "gantt_image_path": "/tmp/roadmap.png"
        })
        mock_client.fetch_gantt_image = AsyncMock(return_value=b"fake_image_bytes")
        mock_client.fetch_excel_file = AsyncMock(return_value=b"fake_excel_bytes")
        mock_client_cls.return_value = mock_client
        
        test_bot = LinmapBot()
        test_bot.api_client = mock_client
        
        # Mock channel
        mock_channel = AsyncMock()
        
        # Run pipeline
        await test_bot._run_pipeline_and_post(mock_channel)
        
        # Assertions
        mock_client.trigger_generation.assert_called_once()
        mock_client.fetch_gantt_image.assert_called_once()
        mock_client.fetch_excel_file.assert_called_once()
        
        mock_channel.send.assert_called_once()
        call_kwargs = mock_channel.send.call_args[1]
        self.assertIn("embed", call_kwargs)
        self.assertIn("files", call_kwargs)
        
        embed = call_kwargs["embed"]
        self.assertEqual(embed.title, "🗺️ UBSI Program - Roadmap Sync")
        self.assertEqual(embed.fields[0].value, "[Open Google Drive Link](https://drive.google.com/file/d/mock-id/view)")
        
        files = call_kwargs["files"]
        self.assertEqual(len(files), 2)
        self.assertIsInstance(files[0], discord.File)
        self.assertEqual(files[0].filename, "roadmap.png")
        self.assertIsInstance(files[1], discord.File)
        self.assertEqual(files[1].filename, "Linear_Roadmap.xlsx")

    @patch("src.bot.discord_client.LinmapAPIClient")
    async def test_bot_run_pipeline_and_post_no_image(self, mock_client_cls):
        # Setup mocks
        mock_client = MagicMock()
        mock_client.trigger_generation = AsyncMock(return_value={
            "status": "success",
            "excel_url": "https://drive.google.com/file/d/mock-id/view"
        })
        mock_client.fetch_gantt_image = AsyncMock(return_value=None)
        mock_client.fetch_excel_file = AsyncMock(return_value=b"fake_excel_bytes")
        mock_client_cls.return_value = mock_client
        
        test_bot = LinmapBot()
        test_bot.api_client = mock_client
        
        # Mock channel
        mock_channel = AsyncMock()
        
        # Run pipeline and assert exception is raised
        with self.assertRaises(RuntimeError) as context:
            await test_bot._run_pipeline_and_post(mock_channel)
            
        self.assertIn("Failed to fetch rendered Gantt chart", str(context.exception))
        mock_channel.send.assert_not_called()

    @patch("src.bot.discord_client.LinmapAPIClient")
    async def test_bot_run_pipeline_and_post_no_excel(self, mock_client_cls):
        # Setup mocks
        mock_client = MagicMock()
        mock_client.trigger_generation = AsyncMock(return_value={
            "status": "success",
            "excel_url": "https://drive.google.com/file/d/mock-id/view"
        })
        mock_client.fetch_gantt_image = AsyncMock(return_value=b"fake_image_bytes")
        mock_client.fetch_excel_file = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client
        
        test_bot = LinmapBot()
        test_bot.api_client = mock_client
        
        # Mock channel
        mock_channel = AsyncMock()
        
        # Run pipeline and assert exception is raised
        with self.assertRaises(RuntimeError) as context:
            await test_bot._run_pipeline_and_post(mock_channel)
            
        self.assertIn("Failed to fetch Excel report", str(context.exception))
        mock_channel.send.assert_not_called()


class TestBotAPIClientFetchImage(unittest.IsolatedAsyncioTestCase):
    
    @patch("src.bot.api_client.httpx.AsyncClient.get")
    async def test_fetch_gantt_image_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"image_binary_data"
        mock_get.return_value = mock_response
        
        client = LinmapAPIClient()
        img_bytes = await client.fetch_gantt_image()
        
        self.assertEqual(img_bytes, b"image_binary_data")
        mock_get.assert_called_once_with(f"{client.base_url}/roadmap/image")

    @patch("src.bot.api_client.httpx.AsyncClient.get")
    async def test_fetch_gantt_image_http_error(self, mock_get):
        mock_get.side_effect = httpx.HTTPError("API error")
        
        client = LinmapAPIClient()
        img_bytes = await client.fetch_gantt_image()
        
        self.assertIsNone(img_bytes)

    @patch("src.bot.api_client.httpx.AsyncClient.get")
    async def test_fetch_excel_file_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"excel_binary_data"
        mock_get.return_value = mock_response
        
        client = LinmapAPIClient()
        excel_bytes = await client.fetch_excel_file()
        
        self.assertEqual(excel_bytes, b"excel_binary_data")
        mock_get.assert_called_once_with(f"{client.base_url}/roadmap/excel")

    @patch("src.bot.api_client.httpx.AsyncClient.get")
    async def test_fetch_excel_file_http_error(self, mock_get):
        mock_get.side_effect = httpx.HTTPError("API error")
        
        client = LinmapAPIClient()
        excel_bytes = await client.fetch_excel_file()
        
        self.assertIsNone(excel_bytes)
