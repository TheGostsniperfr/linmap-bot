import logging
import requests
from typing import Dict, Any
from src.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class TransientAPIError(requests.RequestException):
    """Exception raised for transient API errors that should be retried."""
    pass

class LinearClient:
    """Client wrapper for interacting with the Linear GraphQL API."""
    
    def __init__(self) -> None:
        self.url = "https://api.linear.app/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": settings.LINEAR_API_KEY.get_secret_value()
        }

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout, TransientAPIError)),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Linear API call failed, retrying in {retry_state.next_action.sleep:.2f}s... (Attempt {retry_state.attempt_number})"
        )
    )
    def fetch_roadmap_data(self) -> Dict[str, Any]:
        """
        Fetches active projects, milestones, and issues.
        Filters only non-canceled, non-archived projects (states: backlog, planned, started, paused).
        """
        query = """
        query GetRoadmapData {
          projects(first: 20, filter: { state: { in: ["backlog", "planned", "started", "paused"] } }) {
            nodes {
              id
              name
              startDate
              targetDate
              state
              milestones: projectMilestones(first: 15) {
                nodes {
                  id
                  name
                  targetDate
                }
              }
              issues(first: 100) {
                nodes {
                  id
                  title
                  status: state {
                    name
                  }
                  dueDate
                  assignee {
                    name
                  }
                }
              }
            }
          }
        }
        """
        try:
            response = requests.post(
                self.url, 
                json={"query": query}, 
                headers=self.headers, 
                timeout=15
            )
            
            if response.status_code == 400:
                error_details = response.text
                logger.error(f"Linear GraphQL Validation Error: {error_details}")
                raise RuntimeError(f"Linear API rejected the query: {error_details}")
            
            # Check for transient errors to trigger retry via TransientAPIError
            if response.status_code in (429, 502, 503, 504):
                logger.warning(f"Transient API error ({response.status_code}) received from Linear.")
                raise TransientAPIError(f"HTTP {response.status_code}", response=response)
                
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error(f"GraphQL execution errors: {data['errors']}")
                raise RuntimeError(f"Failed execution due to GraphQL errors: {data['errors']}")
                
            return data.get("data", {})
        except requests.RequestException as e:
            if not isinstance(e, TransientAPIError):
                logger.error(f"Network error while calling Linear API: {e}")
            raise