"""
ReportPortal client wrapper for simplified test result reporting.

This module provides a high-level wrapper around the ReportPortal client
with enhanced logging, error handling, and auto-analysis capabilities.
"""

import requests
import time
from typing import List, Dict, Optional
from loguru import logger

from reportportal_client import RPClient
from reportportal_client.helpers import timestamp
from reportportal.junit_parser import timestamp_rp_to_junit


class ReportPortalClientWrapper:
    """
    High-level wrapper for ReportPortal client operations.
    
    This wrapper provides simplified methods for reporting test results
    with enhanced error handling and logging.
    """
    
    def __init__(self, url: str, project: str, token: str, dry_run: bool = False):
        """
        Initialize the ReportPortal client wrapper.

        Args:
            url: ReportPortal URL
            project: ReportPortal project name
            token: ReportPortal API token
            dry_run: If True, simulate API calls without actually making them
        """
        self.url = url
        self.project = project
        self.token = token
        self.client = None
        self.dry_run = dry_run
        self._mock_id_counter = 0

    def _generate_mock_id(self) -> str:
        """Generate a mock ID for dry-run mode."""
        self._mock_id_counter += 1
        return f"mock-id-{self._mock_id_counter}"

    def start_session(self) -> None:
        """Start the ReportPortal client session."""
        if self.dry_run:
            logger.info("[DRY-RUN] Would start ReportPortal client session")
            logger.info(f"[DRY-RUN] URL: {self.url}, Project: {self.project}")
            return

        try:
            self.client = RPClient(
                endpoint=self.url,
                project=self.project,
                api_key=self.token
            )
            self.client.start()
            logger.info("ReportPortal client session started successfully")
        except Exception as e:
            logger.error(f"Failed to start ReportPortal client session: {e}")
            raise
    
    def terminate_session(self) -> None:
        """Terminate the ReportPortal client session."""
        if self.dry_run:
            logger.info("[DRY-RUN] Would terminate ReportPortal client session")
            return

        if self.client:
            try:
                # Force the client to send all batched requests before terminating
                # The RPClient uses asynchronous batching with a background worker thread
                # We need to ensure all pending requests (especially finish_launch) are
                # sent to the server before calling terminate()

                logger.debug("Flushing pending requests before termination...")

                # WORKAROUND: Give the async worker thread time to process pending requests
                # The RPClient.terminate() should wait for the queue to drain, but there's
                # a known race condition where finish_launch might not complete in time
                # See: https://github.com/reportportal/client-Python/issues
                time.sleep(1.0)

                logger.debug("Terminating ReportPortal client session...")
                self.client.terminate()
                logger.info("ReportPortal client session terminated successfully")
            except Exception as e:
                logger.error(f"Error terminating ReportPortal session: {e}")
                
    def start_launch(self, name: str, start_time: str, description: str = "") -> str:
        """
        Start a new launch in ReportPortal.

        Args:
            name: Launch name
            start_time: Launch start time (timestamp string)
            description: Launch description

        Returns:
            Launch ID
        """
        if self.dry_run:
            mock_id = self._generate_mock_id()
            logger.info(f"[DRY-RUN] Would start launch '{name}' with ID: {mock_id}")
            logger.info(f"[DRY-RUN] Start time: {timestamp_rp_to_junit(start_time)}, Description: {description}")
            return mock_id

        if not self.client:
            raise RuntimeError("Client session not started")

        try:
            launch_id = self.client.start_launch(
                name=name,
                start_time=start_time,
                description=description
            )
            logger.info(f"Started launch '{name}' with ID: {launch_id}")
            logger.debug(f"Start time: {timestamp_rp_to_junit(start_time)}, Description: {description}")
            return launch_id
        except Exception as e:
            logger.error(f"Failed to start launch '{name}': {e}")
            raise
    
    def finish_launch(self, end_time: str, attributes: Optional[List[Dict]] = None,
                     description: Optional[str] = None) -> Dict:
        """
        Finish the current launch.

        Args:
            end_time: Launch end time (timestamp string)
            attributes: Launch attributes
            description: Final launch description

        Returns:
            Launch info dictionary
        """
        if self.dry_run:
            mock_info = {"id": "mock-launch-id", "name": "mock-launch"}
            logger.info(f"[DRY-RUN] Would finish launch with ID: {mock_info['id']}")
            logger.info(f"[DRY-RUN] End time: {timestamp_rp_to_junit(end_time)}, Attributes: {attributes}, Description: {description}")
            return mock_info

        if not self.client:
            raise RuntimeError("Client session not started")

        try:
            logger.debug(f"Finishing launch at {timestamp_rp_to_junit(end_time)}")
            logger.debug(f"Launch attributes: {attributes}")
            logger.debug(f"Launch description: {description}")

            ts_now = timestamp()
            logger.warning(f"Overwriting {end_time=} to {ts_now}, workaround for runaway launches")
            end_time = ts_now

            # Finish the launch with explicit status
            # Status is automatically determined by the client based on test results
            result = self.client.finish_launch(
                end_time=end_time, ## forcing end_time to now(), workaround for runaway launches
                attributes=attributes,
                description=description
            )

            launch_info = self.client.get_launch_info()
            logger.info(f"Finished launch with ID: {launch_info.get('id', 'unknown')}")
            logger.debug(f"End time: {timestamp_rp_to_junit(end_time)}, Attributes: {attributes}, Description: {description}")
            logger.debug(f"Launch info: {launch_info}")
            logger.debug(f"Finish launch result: {result}")
            return launch_info
        except Exception as e:
            logger.error(f"Failed to finish launch: {e}")
            logger.exception(e)
            raise
    
    def start_test_suite(self, name: str, start_time: str,
                        attributes: Optional[List[Dict]] = None,
                        description: Optional[str] = None) -> str:
        """
        Start a test suite.

        Args:
            name: Suite name
            start_time: Suite start time (timestamp string)
            attributes: Suite attributes
            description: Suite description

        Returns:
            Suite item ID
        """
        if self.dry_run:
            mock_id = self._generate_mock_id()
            logger.info(f"[DRY-RUN] Would start test suite '{name}' with ID: {mock_id}")
            logger.info(f"[DRY-RUN] Start time: {timestamp_rp_to_junit(start_time)}, Attributes: {attributes}")
            return mock_id

        if not self.client:
            raise RuntimeError("Client session not started")

        try:
            suite_id = self.client.start_test_item(
                name=name,
                start_time=start_time,
                item_type="SUITE",
                attributes=attributes,
                description=description
            )
            logger.debug(f"Started test suite '{name}' with ID: {suite_id}")
            logger.debug(f"Start time: {timestamp_rp_to_junit(start_time)}, Attributes: {attributes}")
            return suite_id
        except Exception as e:
            logger.error(f"Failed to start test suite '{name}': {e}")
            raise
    
    def finish_test_suite(self, suite_id: str, end_time: str,
                         attributes: Optional[List[Dict]] = None) -> None:
        """
        Finish a test suite.

        Args:
            suite_id: Suite item ID
            end_time: Suite end time (timestamp string)
            attributes: Suite attributes
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would finish test suite with ID: {suite_id}")
            logger.info(f"[DRY-RUN] End time: {timestamp_rp_to_junit(end_time)}, Attributes: {attributes}")
            return

        if not self.client:
            raise RuntimeError("Client session not started")

        try:
            self.client.finish_test_item(
                item_id=suite_id,
                end_time=end_time,
                attributes=attributes
            )
            logger.debug(f"Finished test suite with ID: {suite_id}")
            logger.debug(f"End time: {timestamp_rp_to_junit(end_time)}, Attributes: {attributes}")
        except Exception as e:
            logger.error(f"Failed to finish test suite {suite_id}: {e}")
            raise
    
    def start_test_case(self, name: str, start_time: str, parent_id: str,
                       attributes: Optional[List[Dict]] = None,
                       description: Optional[str] = None,
                       code_ref: Optional[str] = None,
                       test_case_id: Optional[str] = None,
                       retry: bool = False,
                       retry_of: Optional[str] = None) -> str:
        """
        Start a test case.

        Args:
            name: Test case name
            start_time: Test start time (timestamp string)
            parent_id: Parent suite ID
            attributes: Test case attributes
            description: Test case description
            code_ref: Code reference for the test (e.g., "path/to/test.py::test_name")
            test_case_id: Explicit test case identifier for RP history matching
            retry: If True, marks this test case as a retry of a previous attempt
            retry_of: UUID of the original test item this retry references (RP 25.x)

        Returns:
            Test case item ID
        """
        if self.dry_run:
            mock_id = self._generate_mock_id()
            logger.info(f"[DRY-RUN] Would start test case '{name}' with ID: {mock_id}")
            logger.info(f"[DRY-RUN] Parent: {parent_id}, Code ref: {code_ref}, Test case id: {test_case_id}, Retry: {retry}, Retry of: {retry_of}")
            return mock_id

        if not self.client:
            raise RuntimeError("Client session not started")

        try:
            case_id = self.client.start_test_item(
                name=name,
                start_time=start_time,
                item_type="STEP",
                attributes=attributes,
                description=description,
                parent_item_id=parent_id,
                code_ref=code_ref,
                test_case_id=test_case_id,
                retry=retry,
                retry_of=retry_of
            )
            logger.debug(f"Started test case '{name}' with ID: {case_id}")
            logger.debug(f"Parent: {parent_id}, Code ref: {code_ref}, Test case id: {test_case_id}, Retry: {retry}, Retry of: {retry_of}")
            return case_id
        except Exception as e:
            logger.error(f"Failed to start test case '{name}': {e}")
            raise
    
    def finish_test_case(self, case_id: str, end_time: str, status: str,
                        attributes: Optional[List[Dict]] = None) -> None:
        """
        Finish a test case.

        Args:
            case_id: Test case item ID
            end_time: Test end time (timestamp string)
            status: Test status (PASSED, FAILED, SKIPPED, ERROR)
            attributes: Test case attributes
        """
        # Map ERROR to FAILED since ReportPortal doesn't recognize ERROR as a valid status
        # Valid RP statuses: PASSED, FAILED, STOPPED, SKIPPED, INTERRUPTED, CANCELLED, INFO, WARN
        if status == "ERROR":
            status = "FAILED"

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would finish test case {case_id} with status: {status}")
            logger.info(f"[DRY-RUN] End time: {timestamp_rp_to_junit(end_time)}, Attributes: {attributes}")
            return

        if not self.client:
            raise RuntimeError("Client session not started")

        try:
            self.client.finish_test_item(
                item_id=case_id,
                end_time=end_time,
                status=status,
                attributes=attributes
            )
            logger.debug(f"Finished test case {case_id} with status: {status}")
            logger.debug(f"End time: {timestamp_rp_to_junit(end_time)}, Attributes: {attributes}")
        except Exception as e:
            logger.error(f"Failed to finish test case {case_id}: {e}")
            raise
    
    def log_message(self, item_id: str, message: str, level: str = "INFO") -> None:
        """
        Log a message to a test item.

        Args:
            item_id: Test item ID
            message: Log message
            level: Log level (INFO, ERROR, WARN, DEBUG)
        """
        if not message:
            return

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would log {level} message to item {item_id}: {message[:100]}")
            return

        if not self.client:
            return

        try:
            self.client.log(
                time=timestamp(),
                message=message,
                level=level,
                item_id=item_id
            )
            logger.debug(f"Logged {level} message to item {item_id}")
        except Exception as e:
            logger.error(f"Failed to log message to item {item_id}: {e}")
    
    def log_test_outputs(self, case_id: str, system_out: Optional[str], 
                        system_err: Optional[str], failures: List[str], 
                        errors: List[str], skipped: List[str]) -> None:
        """
        Log test outputs, errors, failures, and skip reasons.
        
        Args:
            case_id: Test case item ID
            system_out: Standard output
            system_err: Standard error
            failures: List of failure messages
            skipped: List of skip messages
        """
        # Log failures
        for failure in failures:
            self.log_message(case_id, failure, "ERROR")
        
        # Log Errors
        for error in errors:
            self.log_message(case_id, error, "ERROR")
        
        # Log skip reasons (as ERROR so auto-analysis picks them up)
        for skip in skipped:
            self.log_message(case_id, skip, "ERROR")
        
        # Log system outputs
        if system_out:
            self.log_message(case_id, system_out, "INFO")
        
        if system_err:
            self.log_message(case_id, system_err, "ERROR")


class AutoAnalysisTrigger:
    """
    Handles triggering of auto-analysis for ReportPortal launches.
    """
    
    def __init__(self, url: str, project: str, token: str, dry_run: bool = False):
        """
        Initialize the auto-analysis trigger.

        Args:
            url: ReportPortal URL
            project: ReportPortal project name
            token: ReportPortal API token
            dry_run: If True, simulate API calls without actually making them
        """
        self.url = url
        self.project = project
        self.token = token
        self.dry_run = dry_run
    
    def trigger_auto_analysis(self, launch_id: str) -> bool:
        """
        Trigger auto-analysis for a specific launch.

        Args:
            launch_id: Launch UUID

        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would trigger auto-analysis for launch {launch_id}")
            logger.info(f"[DRY-RUN] URL: {self.url}/api/v1/{self.project}/launch/analyze")
            return True

        logger.debug(f"Triggering auto-analysis for launch {launch_id}")

        try:
            response = requests.post(
                url=f"{self.url}/api/v1/{self.project}/launch/analyze",
                headers={
                    'Authorization': f'bearer {self.token}',
                    'Content-type': 'application/json',
                    'accept': '*/*'
                },
                json={
                    "analyzeItemsMode": ["TO_INVESTIGATE"],
                    "analyzerMode": "ALL",
                    "analyzerTypeName": "autoAnalyzer",
                    "launchId": launch_id,
                },
            )
            response.raise_for_status()
            logger.info(f"Auto-analysis triggered successfully for launch {launch_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Auto analysis trigger request failed for launch {launch_id}: {e}")
            return False


def create_rp_client(url: str, project: str, token: str, dry_run: bool = False) -> ReportPortalClientWrapper:
    """
    Factory function to create a ReportPortal client wrapper.

    Args:
        url: ReportPortal URL
        project: ReportPortal project name
        token: ReportPortal API token
        dry_run: If True, simulate API calls without actually making them

    Returns:
        Configured ReportPortalClientWrapper instance
    """
    return ReportPortalClientWrapper(url, project, token, dry_run)