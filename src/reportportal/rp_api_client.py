"""
ReportPortal API Client

Provides both class-based and function-based interfaces for interacting
with ReportPortal REST API.
"""

import requests
from typing import List, Dict, Optional, Any
from datetime import datetime
from loguru import logger


# Constants
DEFAULT_PAGE_SIZE = 1000
DEFAULT_TIMEOUT = 30  # seconds


class ReportPortalAPIError(Exception):
    """Exception raised for ReportPortal API errors."""
    pass


# =============================================================================
# Module-Level Constants
# =============================================================================


# =============================================================================
# ReportPortal API Client Class
# =============================================================================

class ReportPortalAPIClient:
    """
    Class-based client for ReportPortal REST API operations.

    This client provides methods for querying launches, test items,
    and triggering analysis in ReportPortal.
    """

    def __init__(self, url: str, project: str, token: str):
        """
        Initialize the ReportPortal API client.

        Args:
            url: ReportPortal URL (e.g., https://reportportal.example.com)
            project: ReportPortal project name
            token: ReportPortal API token
        """
        self.url = url
        self.project = project
        self.token = token

    def build_headers(self) -> Dict[str, str]:
        """
        Build standard ReportPortal API headers.

        Returns:
            Dictionary of HTTP headers
        """
        return {
            'Authorization': f'bearer {self.token}',
            'Content-type': 'application/json',
            'accept': '*/*'
        }

    @staticmethod
    def normalize_timestamp(timestamp: Optional[Any]) -> Optional[int]:
        """
        Normalize timestamp to Unix milliseconds (integer).

        ReportPortal API changed from returning Unix milliseconds to ISO format strings.
        This method handles both formats for backward compatibility.

        Args:
            timestamp: Either ISO format string or Unix milliseconds (int/float)

        Returns:
            Unix timestamp in milliseconds as integer, or None if input is None
        """
        if timestamp is None:
            return None

        # Already in Unix milliseconds format
        if isinstance(timestamp, (int, float)):
            return int(timestamp)

        # ISO format string - convert to Unix milliseconds
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return int(dt.timestamp() * 1000)
            except (ValueError, AttributeError) as e:
                logger.warning("Failed to parse timestamp '{}': {}", timestamp, e)
                return None

        logger.warning("Timestamp was unexpected type: {}", type(timestamp))
        return None

    def normalize_timestamps_in_dict(self, data: Dict[str, Any],
                                     timestamp_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Normalize timestamp fields in a dictionary.

        Args:
            data: Dictionary potentially containing timestamp fields
            timestamp_fields: List of field names to normalize (default: startTime, endTime)

        Returns:
            Dictionary with normalized timestamps
        """
        if timestamp_fields is None:
            timestamp_fields = ['startTime', 'endTime']

        for field in timestamp_fields:
            if field in data:
                data[field] = self.normalize_timestamp(data[field])

        return data

    def build_url(self, resource: str, **params) -> str:
        """
        Build ReportPortal API URL with query parameters.

        Args:
            resource: API resource path (e.g., 'launch', 'item')
            **params: Query parameters

        Returns:
            Complete URL string
        """
        base_url = f'{self.url}/api/v1/{self.project}/{resource}'
        if params:
            query_parts = [f'{k}={v}' for k, v in params.items() if v is not None]
            if query_parts:
                base_url += '?' + '&'.join(query_parts)
        return base_url

    @staticmethod
    def build_filter_dict(status: Optional[str] = None,
                         name: Optional[str] = None,
                         name_contains: Optional[str] = None,
                         **custom_filters) -> Dict[str, Any]:
        """
        Build a filter dictionary for API queries.

        Args:
            status: Filter by status (e.g., 'PASSED', 'FAILED')
            name: Filter by exact name
            name_contains: Filter by name containing string
            **custom_filters: Additional custom filters

        Returns:
            Dictionary of filters
        """
        filters = {}

        if status:
            filters['filter.eq.status'] = status
        if name:
            filters['filter.eq.name'] = name
        if name_contains:
            filters['filter.cnt.name'] = name_contains

        filters.update(custom_filters)

        return {k: v for k, v in filters.items() if v is not None}

    def _request(self, request_func, endpoint: str):
        """
        Common error handling wrapper for HTTP requests.

        Args:
            request_func: Callable that performs the actual HTTP request
            endpoint: API endpoint path (for error messages)

        Returns:
            Response JSON data or empty dict

        Raises:
            ReportPortalAPIError: On API errors
        """
        try:
            response = request_func()
            response.raise_for_status()
            return response.json() if response.content else {}

        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed for {endpoint}: {e}"
            logger.error(error_msg)
            raise ReportPortalAPIError(error_msg) from e
        except (KeyError, ValueError) as e:
            error_msg = f"Failed to parse API response from {endpoint}: {e}"
            logger.error(error_msg)
            raise ReportPortalAPIError(error_msg) from e

    def _get(self, endpoint: str, timeout: int = DEFAULT_TIMEOUT) -> Dict:
        """
        Perform a GET request.

        Args:
            endpoint: API endpoint path
            timeout: Request timeout in seconds

        Returns:
            Response JSON data

        Raises:
            ReportPortalAPIError: On API errors
        """
        url = f"{self.url}{endpoint}"
        headers = self.build_headers()
        return self._request(
            lambda: requests.get(url, headers=headers, timeout=timeout),
            endpoint
        )

    def _post(self, endpoint: str, json_data: Optional[Dict] = None, timeout: int = DEFAULT_TIMEOUT) -> Dict:
        """
        Perform a POST request.

        Args:
            endpoint: API endpoint path
            json_data: JSON data for request body
            timeout: Request timeout in seconds

        Returns:
            Response JSON data

        Raises:
            ReportPortalAPIError: On API errors
        """
        url = f"{self.url}{endpoint}"
        headers = self.build_headers()
        return self._request(
            lambda: requests.post(url, headers=headers, json=json_data, timeout=timeout),
            endpoint
        )

    def _put(self, endpoint: str, json_data: Optional[Dict] = None, timeout: int = DEFAULT_TIMEOUT) -> Dict:
        """
        Perform a PUT request.

        Args:
            endpoint: API endpoint path
            json_data: JSON data for request body
            timeout: Request timeout in seconds

        Returns:
            Response JSON data

        Raises:
            ReportPortalAPIError: On API errors
        """
        url = f"{self.url}{endpoint}"
        headers = self.build_headers()
        return self._request(
            lambda: requests.put(url, headers=headers, json=json_data, timeout=timeout),
            endpoint
        )

    def _delete(self, endpoint: str, timeout: int = DEFAULT_TIMEOUT) -> Dict:
        """
        Perform a DELETE request.

        Args:
            endpoint: API endpoint path
            timeout: Request timeout in seconds

        Returns:
            Response JSON data

        Raises:
            ReportPortalAPIError: On API errors
        """
        url = f"{self.url}{endpoint}"
        headers = self.build_headers()
        return self._request(
            lambda: requests.delete(url, headers=headers, timeout=timeout),
            endpoint
        )

    # =========================================================================
    # Launch Operations
    # =========================================================================

    def get_launches(self,
                    sort_by: str = 'startTime,DESC',
                    page_size: int = DEFAULT_PAGE_SIZE,
                    filters: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """
        Get launches from ReportPortal project.

        Args:
            sort_by: Sort parameter (default: newest first)
            page_size: Number of items per page
            filters: Additional filters as dict (e.g., {'filter.eq.name': 'test'})

        Returns:
            List of launch dictionaries with normalized timestamps (Unix milliseconds)

        Raises:
            ReportPortalAPIError: On API errors
        """
        logger.debug(f"Fetching launches from project '{self.project}'")

        # Build query parameters
        params = {'page.sort': sort_by, 'page.size': page_size}
        if filters:
            params.update(filters)

        query_string = '&'.join(f'{k}={v}' for k, v in params.items() if v is not None)
        endpoint = f'/api/v1/{self.project}/launch?{query_string}'

        data = self._get(endpoint)
        launches = data.get('content', [])

        # Normalize timestamps in all launches
        launches = [self.normalize_timestamps_in_dict(launch) for launch in launches]

        logger.debug(f"Retrieved {len(launches)} launches")
        return launches

    def get_launch_by_id(self, launch_id: str) -> Dict:
        """
        Get a specific launch by ID.

        Args:
            launch_id: Launch UUID

        Returns:
            Launch dictionary with normalized timestamps (Unix milliseconds)

        Raises:
            ReportPortalAPIError: On API errors
        """
        logger.debug(f"Fetching launch {launch_id}")
        endpoint = f'/api/v1/{self.project}/launch/{launch_id}'
        launch = self._get(endpoint)
        return self.normalize_timestamps_in_dict(launch)

    # =========================================================================
    # Test Item Operations
    # =========================================================================

    def get_test_items(self,
                      launch_id: str,
                      page_size: int = DEFAULT_PAGE_SIZE,
                      filters: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """
        Get test items for a specific launch.

        Args:
            launch_id: Launch UUID
            page_size: Number of items per page
            filters: Additional filters (e.g., {'filter.eq.status': 'FAILED'})

        Returns:
            List of test item dictionaries with normalized timestamps (Unix milliseconds)

        Raises:
            ReportPortalAPIError: On API errors
        """
        logger.debug(f"Fetching test items for launch {launch_id}")

        # Build query parameters
        params = {
            'filter.eq.launchId': launch_id,
            'page.size': page_size
        }
        if filters:
            params.update(filters)

        query_string = '&'.join(f'{k}={v}' for k, v in params.items() if v is not None)
        endpoint = f'/api/v1/{self.project}/item?{query_string}'

        data = self._get(endpoint)
        items = data.get('content', [])

        # Normalize timestamps in all test items
        items = [self.normalize_timestamps_in_dict(item) for item in items]

        logger.debug(f"Retrieved {len(items)} test items")
        return items

    def get_test_item_by_id(self, item_id: str) -> Dict:
        """
        Get a specific test item by ID.

        Args:
            item_id: Test item UUID

        Returns:
            Test item dictionary with normalized timestamps (Unix milliseconds)

        Raises:
            ReportPortalAPIError: On API errors
        """
        logger.debug(f"Fetching test item {item_id}")
        endpoint = f'/api/v1/{self.project}/item/{item_id}'
        item = self._get(endpoint)
        return self.normalize_timestamps_in_dict(item)

    # =========================================================================
    # Analysis Operations
    # =========================================================================

    def trigger_analysis(self,
                        launch_id: str,
                        analyze_items_mode: Optional[List[str]] = None,
                        analyzer_mode: str = "ALL") -> bool:
        """
        Trigger auto-analysis for a launch.

        Args:
            launch_id: Launch UUID
            analyze_items_mode: Items to analyze (default: ["TO_INVESTIGATE"])
            analyzer_mode: Analysis mode (default: "ALL")

        Returns:
            True if successful

        Raises:
            ReportPortalAPIError: On API errors
        """
        if analyze_items_mode is None:
            analyze_items_mode = ["TO_INVESTIGATE"]

        logger.debug(f"Triggering auto-analysis for launch {launch_id}")

        endpoint = f'/api/v1/{self.project}/launch/analyze'
        json_data = {
            "analyzeItemsMode": analyze_items_mode,
            "analyzerMode": analyzer_mode,
            "analyzerTypeName": "autoAnalyzer",
            "launchId": launch_id,
        }

        self._post(endpoint, json_data=json_data)
        logger.info(f"Auto-analysis triggered successfully for launch {launch_id}")
        return True


# =============================================================================
# Factory Function
# =============================================================================

def create_api_client(url: str, project: str, token: str) -> ReportPortalAPIClient:
    """
    Factory function to create a ReportPortal API client.

    Args:
        url: ReportPortal URL
        project: ReportPortal project name
        token: ReportPortal API token

    Returns:
        Configured ReportPortalAPIClient instance
    """
    return ReportPortalAPIClient(url, project, token)
