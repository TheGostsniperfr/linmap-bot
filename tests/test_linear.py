import unittest
from unittest.mock import patch, MagicMock
import requests
from src.linear.graphql_client import LinearClient, TransientAPIError

class TestLinearClient(unittest.TestCase):
    
    @patch("src.linear.graphql_client.requests.post")
    def test_fetch_roadmap_data_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "projects": {
                    "nodes": [
                        {
                            "id": "1",
                            "name": "Project Alpha",
                            "targetDate": "2026-12-31",
                            "state": "started",
                            "milestones": {"nodes": []},
                            "issues": {"nodes": []}
                        }
                    ]
                }
            }
        }
        mock_post.return_value = mock_response

        client = LinearClient()
        data = client.fetch_roadmap_data()
        
        self.assertIn("projects", data)
        self.assertEqual(data["projects"]["nodes"][0]["name"], "Project Alpha")
        mock_post.assert_called_once()

    @patch("src.linear.graphql_client.requests.post")
    def test_fetch_roadmap_data_transient_retry(self, mock_post):
        # First call: 502 Bad Gateway
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 502

        # Second call: 200 Success
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "data": {
                "projects": {
                    "nodes": []
                }
            }
        }

        mock_post.side_effect = [mock_response_fail, mock_response_success]

        client = LinearClient()
        data = client.fetch_roadmap_data()
        
        # Verify the client retried on 502 and completed successfully on attempt 2
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(data["projects"]["nodes"], [])
        
    @patch("src.linear.graphql_client.requests.post")
    def test_fetch_roadmap_data_graphql_errors(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [{"message": "Unauthorized"}]
        }
        mock_post.return_value = mock_response

        client = LinearClient()
        
        with self.assertRaises(RuntimeError) as context:
            client.fetch_roadmap_data()
        
        self.assertIn("GraphQL errors", str(context.exception))
